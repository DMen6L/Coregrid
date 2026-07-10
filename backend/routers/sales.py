from typing import Literal

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload

from app.models import Product, Sale, StockMovement, StockMovementLine
from app.schemas import PaginatedResponse, SaleCreate, SaleResponse
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/sales", tags=["sales"])
SaleOrder = Literal["oldest", "latest"]


@router.post("", response_model=SaleResponse, status_code=201)
def add_sale(sale_data: SaleCreate, db: DbSession) -> Sale:
    product_ids = [line.product_id for line in sale_data.lines]
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
        movement_type="out",
        note=sale_data.note,
    )
    new_sale = Sale(
        stock_movement=new_movement,
        note=sale_data.note,
    )
    db.add(new_sale)

    for line_data in sale_data.lines:
        product = products_by_id[line_data.product_id]
        quantity_before = product.quantity
        quantity_after = quantity_before - line_data.quantity

        if quantity_after < 0:
            raise HTTPException(
                status_code=422,
                detail="Sale would make product quantity negative",
            )

        product.quantity = quantity_after
        new_movement.lines.append(
            StockMovementLine(
                product_id=product.id,
                quantity_delta=-line_data.quantity,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                unit_price_snapshot=line_data.unit_price,
                quantity_unit_snapshot=product.quantity_unit,
            )
        )

    commit_or_raise(db)

    return get_sale_or_404(new_sale.id, db)


@router.get("", response_model=PaginatedResponse[SaleResponse], status_code=200)
def get_sales(
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = DEFAULT_PAGE_SIZE,
    order: SaleOrder = "latest",
) -> dict[str, object]:
    sort_column = Sale.id if order == "oldest" else Sale.id.desc()
    query = (
        db.query(Sale)
        .options(
            selectinload(Sale.stock_movement).selectinload(StockMovement.lines),
        )
        .order_by(sort_column)
    )

    return paginate(query, page, page_size)


@router.get("/{id}", response_model=SaleResponse, status_code=200)
def get_sale(id: int, db: DbSession) -> Sale:
    return get_sale_or_404(id, db)


def get_sale_or_404(id: int, db: DbSession) -> Sale:
    sale = (
        db.query(Sale)
        .options(
            selectinload(Sale.stock_movement).selectinload(StockMovement.lines),
        )
        .filter(Sale.id == id)
        .one_or_none()
    )

    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")

    return sale
