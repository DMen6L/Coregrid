from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product, Tag
from app.pricing import calculate_floor_price
from app.schemas import PaginatedResponse, ProductCreate, ProductResponse
from app.tags import get_or_create_tags
from devs import DbSession
from errors import commit_or_raise


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductResponse], status_code=200)
def get_product_by_name(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    statement_total = select(func.count()).select_from(Product)
    statement_products = (
        select(Product)
        .order_by(Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    if search and (search := search.strip()):
        statement_total = statement_total.where(Product.name.ilike(f"%{search}%"))
        statement_products = statement_products.where(Product.name.ilike(f"%{search}%"))

    total = db.scalar(statement_total) or 0

    products = list(db.scalars(statement_products).all())
    items = [ProductResponse.model_validate(product) for product in products]

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse[ProductResponse](
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.post("", response_model=ProductResponse, status_code=201)
def add_product(db: DbSession, product_data: ProductCreate):
    product_values = product_data.model_dump(
        exclude={"tags"},
    )

    if product_values["sale_price"] is None:
        product_values["sale_price"] = calculate_floor_price(
            product_data.purchase_price,
            product_data.margin_percent,
        )

    tags = get_or_create_tags(db, product_data.tags)

    product = Product(
        **product_values,
        tags=tags,
    )

    db.add(product)
    commit_or_raise(db)
    db.refresh(product)

    return product
