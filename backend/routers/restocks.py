from datetime import datetime, date, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import Product, Restock, RestockLine
from app.schemas import PaginatedResponse, RestockCreate, RestockResponse
from devs import DbSession
from errors import commit_or_raise
from utils import paginate


router = APIRouter(prefix="/restocks", tags=["restocks"])


@router.get("", response_model=PaginatedResponse[RestockResponse], status_code=200)
def get_restocks(
    db: DbSession,
    date_from: Annotated[
        date | None,
        Query(alias="from"),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(alias="to"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    statement = (
        select(Restock)
        .options(selectinload(Restock.lines))
        .order_by(Restock.created_at.desc(), Restock.id.desc())
    )
    count_statement = select(func.count(Restock.id)).select_from(Restock)

    if date_from is not None:
        start_datetime = datetime.combine(date_from, time.min)
        statement = statement.where(
            Restock.created_at >= start_datetime,
        )
        count_statement = count_statement.where(
            Restock.created_at >= start_datetime,
        )

    if date_to is not None:
        end_datetime = datetime.combine(
            date_to + timedelta(days=1),
            time.min,
        )
        statement = statement.where(
            Restock.created_at < end_datetime,
        )
        count_statement = count_statement.where(
            Restock.created_at >= end_datetime,
        )

    return paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=RestockResponse,
    )


@router.post(
    "",
    response_model=RestockResponse,
    status_code=201,
)
def add_restock(
    db: DbSession,
    restock_data: RestockCreate,
):
    product_ids = {line.product_id for line in restock_data.lines}

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

    restock = Restock(note=restock_data.note)

    for line_data in restock_data.lines:
        product = products_by_id[line_data.product_id]

        product.quantity += line_data.restock_quantity

        restock.lines.append(
            RestockLine(
                product=product,
                restock_quantity=line_data.restock_quantity,
                unit_cost_snapshot=line_data.unit_cost_snapshot,
                quantity_unit_snapshot=line_data.quantity_unit_snapshot,
            )
        )

    db.add(restock)
    commit_or_raise(db)

    db.refresh(restock)
    db.refresh(restock, attribute_names=["lines"])

    return restock
