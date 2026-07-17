from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import Integer, func, select, type_coerce

from app.models import Product
from app.pricing import calculate_floor_price
from app.schemas import PaginatedResponse, ProductCreate, ProductResponse
from app.tags import get_or_create_tags
from devs import DbSession
from errors import commit_or_raise
from utils import paginate


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductResponse], status_code=200)
def get_product_by_name(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    statement = select(Product).order_by(Product.id)
    count_statement = select(type_coerce(func.count(Product.id), Integer)).select_from(
        Product
    )

    if search and (search := search.strip()):
        condition = Product.name.ilike(f"%{search}%")

        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    return paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=ProductResponse,
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
