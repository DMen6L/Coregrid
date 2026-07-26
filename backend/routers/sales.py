from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import ProductSupplier, Sale, SaleLine
from app.schemas import PaginatedResponse, SaleCreate, SaleResponse, SaleSummaryResponse
from devs import DbSession
from errors import commit_or_raise
from utils import aggr_paginate, paginate


router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("", response_model=PaginatedResponse[SaleSummaryResponse], status_code=200)
def get_sales(
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    statement = (
        select(
            Sale.id.label("id"),
            Sale.note.label("note"),
            Sale.created_at.label("created_at"),
            func.coalesce(
                func.sum(SaleLine.sale_quantity * SaleLine.unit_sale_price_snapshot),
                0,
            ).label("revenue"),
            func.count(SaleLine.id).label("lines_count"),
        )
        .select_from(Sale)
        .join(Sale.lines)
        .group_by(Sale.id, Sale.note, Sale.created_at)
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

    return aggr_paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=SaleSummaryResponse,
    )


@router.post("", response_model=SaleResponse, status_code=201)
def add_sale(db: DbSession, sale_data: SaleCreate):
    product_supplier_ids = {line.product_supplier_id for line in sale_data.lines}

    product_suppliers = list(
        db.scalars(
            select(ProductSupplier)
            .where(ProductSupplier.id.in_(product_supplier_ids))
            .with_for_update()
        ).all()
    )

    product_suppliers_by_id = {
        product_supplier.id: product_supplier for product_supplier in product_suppliers
    }

    missing_product_supplier_ids = product_supplier_ids - product_suppliers_by_id.keys()

    if missing_product_supplier_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Some product-supplier links were not found.",
                "product_supplier_ids": sorted(missing_product_supplier_ids),
            },
        )

    sale = Sale(note=sale_data.note)

    for line_data in sale_data.lines:
        product_supplier = product_suppliers_by_id[line_data.product_supplier_id]

        if product_supplier.quantity < line_data.sale_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Sale quantity exceeds available stock.",
                    "product_supplier_id": product_supplier.id,
                    "available_quantity": product_supplier.quantity,
                    "requested_quantity": line_data.sale_quantity,
                },
            )

        product_supplier.quantity -= line_data.sale_quantity

        sale.lines.append(
            SaleLine(
                product_supplier=product_supplier,
                sale_quantity=line_data.sale_quantity,
                unit_cost_snapshot=product_supplier.purchase_price,
                unit_sale_price_snapshot=product_supplier.sale_price,
                quantity_unit_snapshot=product_supplier.product.quantity_unit,
            )
        )

    db.add(sale)
    commit_or_raise(db)

    db.refresh(sale)
    db.refresh(sale, attribute_names=["lines"])

    return sale
