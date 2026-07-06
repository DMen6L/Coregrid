from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.models import Product, StockMovement, StockMovementLine
from app.schemas import (
    PaginatedResponse,
    StockMovementCreate,
    StockMovementResponse,
    StockMovementSalesSummaryResponse,
)
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(tags=["stock movements"])
StockMovementOrder = Literal["oldest", "latest"]


@router.post("/stock-movements", response_model=StockMovementResponse, status_code=201)
def add_stock_movement(
    movement_data: StockMovementCreate,
    db: DbSession,
) -> StockMovement:
    product_ids = [line.product_id for line in movement_data.lines]
    products = (
        db.query(Product)
        .filter(Product.id.in_(product_ids))
        .with_for_update()
        .all()
    )
    products_by_id = {product.id: product for product in products}

    for product_id in product_ids:
        if product_id not in products_by_id:
            raise HTTPException(status_code=404, detail="Product not found")

    new_movement = StockMovement(
        movement_type=movement_data.movement_type,
        note=movement_data.note,
    )
    db.add(new_movement)

    for line_data in movement_data.lines:
        product = products_by_id[line_data.product_id]
        quantity_before = product.quantity
        quantity_after = quantity_before + line_data.quantity_delta

        if quantity_after < 0:
            raise HTTPException(
                status_code=422,
                detail="Stock movement would make product quantity negative",
            )

        product.quantity = quantity_after
        new_movement.lines.append(
            StockMovementLine(
                product_id=product.id,
                quantity_delta=line_data.quantity_delta,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                unit_price_snapshot=product.sale_price,
                quantity_unit_snapshot=product.quantity_unit,
            )
        )

    commit_or_raise(db)
    db.refresh(new_movement)

    return new_movement


@router.get(
    "/stock-movements",
    response_model=PaginatedResponse[StockMovementResponse],
)
def get_stock_movements(
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = DEFAULT_PAGE_SIZE,
    order: StockMovementOrder = "oldest",
) -> dict[str, object]:
    sort_column = StockMovement.id.desc() if order == "latest" else StockMovement.id
    query = (
        db.query(StockMovement)
        .options(selectinload(StockMovement.lines))
        .order_by(sort_column)
    )

    return paginate(query, page, page_size)


@router.get(
    "/stock-movements/sales-summary",
    response_model=StockMovementSalesSummaryResponse,
)
def get_stock_movement_sales_summary(
    db: DbSession,
    date_from: date,
    date_to: date,
) -> StockMovementSalesSummaryResponse:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from cannot be after date_to")

    start_at = datetime.combine(date_from, time.min)
    end_at = datetime.combine(date_to + timedelta(days=1), time.min)

    sales_filters = (
        StockMovement.movement_type == "out",
        StockMovement.created_at >= start_at,
        StockMovement.created_at < end_at,
    )

    revenue, units_sold, sale_operations = (
        db.query(
            func.coalesce(
                func.sum(
                    func.abs(StockMovementLine.quantity_delta)
                    * func.coalesce(StockMovementLine.unit_price_snapshot, 0)
                ),
                0,
            ),
            func.coalesce(func.sum(func.abs(StockMovementLine.quantity_delta)), 0),
            func.count(func.distinct(StockMovement.id)),
        )
        .join(StockMovementLine)
        .filter(*sales_filters)
        .one()
    )
    units_sold_by_unit = (
        db.query(
            StockMovementLine.quantity_unit_snapshot,
            func.coalesce(func.sum(func.abs(StockMovementLine.quantity_delta)), 0),
        )
        .join(StockMovement, StockMovementLine.movement_id == StockMovement.id)
        .filter(*sales_filters)
        .group_by(StockMovementLine.quantity_unit_snapshot)
        .order_by(StockMovementLine.quantity_unit_snapshot)
        .all()
    )
    sales_day = func.date(StockMovement.created_at).label("sales_day")
    daily_rows = (
        db.query(
            sales_day,
            func.coalesce(
                func.sum(
                    func.abs(StockMovementLine.quantity_delta)
                    * func.coalesce(StockMovementLine.unit_price_snapshot, 0)
                ),
                0,
            ),
            func.coalesce(func.sum(func.abs(StockMovementLine.quantity_delta)), 0),
            func.count(func.distinct(StockMovement.id)),
        )
        .join(StockMovementLine)
        .filter(*sales_filters)
        .group_by(sales_day)
        .order_by(sales_day)
        .all()
    )
    daily_unit_rows = (
        db.query(
            sales_day,
            StockMovementLine.quantity_unit_snapshot,
            func.coalesce(func.sum(func.abs(StockMovementLine.quantity_delta)), 0),
        )
        .join(StockMovementLine)
        .filter(*sales_filters)
        .group_by(sales_day, StockMovementLine.quantity_unit_snapshot)
        .order_by(sales_day, StockMovementLine.quantity_unit_snapshot)
        .all()
    )
    daily_totals_by_date = {
        normalize_sales_summary_date(sales_date): {
            "date": normalize_sales_summary_date(sales_date),
            "revenue": int(daily_revenue),
            "units_sold": int(daily_units_sold),
            "units_sold_by_unit": [],
            "sale_operations": int(daily_sale_operations),
        }
        for (
            sales_date,
            daily_revenue,
            daily_units_sold,
            daily_sale_operations,
        ) in daily_rows
    }

    for sales_date, quantity_unit, quantity in daily_unit_rows:
        daily_total = daily_totals_by_date[normalize_sales_summary_date(sales_date)]
        daily_total["units_sold_by_unit"].append(
            {
                "quantity_unit": quantity_unit,
                "quantity": int(quantity),
            }
        )

    daily_totals = []
    current_date = date_from
    while current_date <= date_to:
        daily_totals.append(
            daily_totals_by_date.get(
                current_date,
                {
                    "date": current_date,
                    "revenue": 0,
                    "units_sold": 0,
                    "units_sold_by_unit": [],
                    "sale_operations": 0,
                },
            )
        )
        current_date += timedelta(days=1)

    return StockMovementSalesSummaryResponse(
        revenue=int(revenue),
        units_sold=int(units_sold),
        units_sold_by_unit=[
            {
                "quantity_unit": quantity_unit,
                "quantity": int(quantity),
            }
            for quantity_unit, quantity in units_sold_by_unit
        ],
        daily_totals=daily_totals,
        sale_operations=int(sale_operations),
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/stock-movements/{id}", response_model=StockMovementResponse)
def get_stock_movement(id: int, db: DbSession) -> StockMovement:
    movement = (
        db.query(StockMovement)
        .options(selectinload(StockMovement.lines))
        .filter(StockMovement.id == id)
        .one_or_none()
    )

    if movement is None:
        raise HTTPException(status_code=404, detail="Stock movement not found")

    return movement


def normalize_sales_summary_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()

    return value


@router.get(
    "/products/{product_id}/movements",
    response_model=PaginatedResponse[StockMovementResponse],
)
def get_product_stock_movements(
    product_id: int,
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = DEFAULT_PAGE_SIZE,
) -> dict[str, object]:
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    query = (
        db.query(StockMovement)
        .join(StockMovementLine)
        .options(selectinload(StockMovement.lines))
        .filter(StockMovementLine.product_id == product_id)
        .order_by(StockMovement.id)
    )

    return paginate(query, page, page_size)
