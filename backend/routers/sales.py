from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import Product, Sale, SaleLine
from app.schemas import PaginatedResponse, SaleCreate, SaleResponse
from devs import DbSession
from errors import commit_or_raise
from utils import paginate


router = APIRouter(prefix="/sales", tags=["salees"])


@router.get("", response_model=PaginatedResponse[SaleResponse], status_code=200)
def get_sales(
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="drom")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    statement = (
        select(Sale)
        .options(selectinload(Sale.lines))
        .order_by(Sale.created_at.desc(), Sale.id.desc())
    )
    count_statement = select(func.count(Sale.id)).select_from(Sale)

    if date_from is not None:
        start_datetime = datetime.combine(date_from, time.min)
        statement = statement.where(
            Sale.created_at >= start_datetime,
        )
        count_statement = count_statement.where(
            Sale.created_at >= start_datetime,
        )

    if date_to is not None:
        end_datetime = datetime.combine(date_to + timedelta(days=1), time.min)
        statement = statement.where(
            Sale.created_at < end_datetime,
        )
        count_statement = count_statement.where(
            Sale.created_at < end_datetime,
        )

    return paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=SaleResponse,
    )


@router.post("", response_model=SaleResponse, status_code=201)
def add_sale(db: DbSession, sale_data: SaleCreate):
    product_ids = {line.product_id for line in sale_data.lines}

    products = list(
        db.scalars(
            select(Product).where(Product.id.in_(product_ids)).with_for_update()
        ).all()
    )

    products_by_id = {product.id: product for product in products}

    missing_product_ids = product_ids - products_by_id.keys()

    if missing_product_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Some products were not found.",
                "product_ids": sorted(missing_product_ids),
            },
        )

    sale = Sale(note=sale_data.note)

    for line_data in sale_data.lines:
        product = products_by_id[line_data.product_id]

        product.quantity -= line_data.sale_quantity

        sale.lines.append(
            SaleLine(
                product=product,
                sale_quantity=line_data.sale_quantity,
                unit_cost_snapshot=product.purchase_price,
                unit_sale_price_snapshot=product.sale_price,
                quantity_unit_snapshot=product.quantity_unit,
            )
        )

    db.add(sale)
    commit_or_raise(db)

    db.refresh(sale)
    db.refresh(sale, attribute_names=["lines"])

    return sale
