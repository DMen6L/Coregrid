from datetime import datetime, date, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import ProductSupplier, Restock, RestockLine, WorkspaceMembership
from app.schemas import (
    PaginatedResponse,
    RestockCreate,
    RestockResponse,
    RestockSummaryResponse,
)
from helpers.dependencies import DbSession, require_workspace_membership
from helpers.pagination import aggr_paginate
from helpers.transactions import commit_or_raise


router = APIRouter(prefix="/workspaces/{workspace_id}/restocks", tags=["restocks"])


@router.get(
    "",
    response_model=PaginatedResponse[RestockSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_restocks(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
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
        select(
            Restock.id.label("id"),
            Restock.note.label("note"),
            Restock.created_at.label("created_at"),
            func.coalesce(
                func.sum(RestockLine.restock_quantity * RestockLine.unit_cost_snapshot),
                0,
            ).label("costs"),
            func.count(RestockLine.id).label("lines_count"),
        )
        .select_from(Restock)
        .where(Restock.workspace_id == membership.workspace_id)
        .join(Restock.lines)
        .group_by(Restock.id, Restock.note, Restock.created_at)
        .order_by(Restock.created_at.desc(), Restock.id.desc())
    )
    count_statement = (
        select(func.count(Restock.id))
        .select_from(Restock)
        .where(Restock.workspace_id == membership.workspace_id)
    )

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
            Restock.created_at < end_datetime,
        )

    return aggr_paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=RestockSummaryResponse,
    )


@router.get(
    "/{restock_id}",
    response_model=RestockResponse,
    status_code=status.HTTP_200_OK,
)
def get_restock_by_id(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    restock_id: Annotated[int, Path(gt=0)],
):
    statement = (
        select(Restock)
        .options(
            selectinload(Restock.lines)
            .selectinload(RestockLine.product_supplier)
            .selectinload(ProductSupplier.product),
            selectinload(Restock.lines)
            .selectinload(RestockLine.product_supplier)
            .selectinload(ProductSupplier.supplier),
        )
        .where(
            Restock.id == restock_id,
            Restock.workspace_id == membership.workspace_id,
        )
    )
    restock = db.scalars(statement).one_or_none()

    if restock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restock with such id doesn't exist.",
        )

    return restock


@router.post(
    "",
    response_model=RestockResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_restock(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    restock_data: RestockCreate,
) -> Restock:
    product_supplier_ids = {line.product_supplier_id for line in restock_data.lines}

    product_suppliers = list(
        db.scalars(
            select(ProductSupplier)
            .options(selectinload(ProductSupplier.product))
            .where(
                ProductSupplier.id.in_(product_supplier_ids),
                ProductSupplier.workspace_id == membership.workspace_id,
            )
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

    restock = Restock(
        note=restock_data.note,
        workspace_id=membership.workspace_id,
    )

    for line_data in restock_data.lines:
        product_supplier = product_suppliers_by_id[line_data.product_supplier_id]

        product_supplier.quantity += line_data.restock_quantity

        restock.lines.append(
            RestockLine(
                product_supplier=product_supplier,
                restock_quantity=line_data.restock_quantity,
                unit_cost_snapshot=(
                    line_data.unit_cost_snapshot
                    if line_data.unit_cost_snapshot is not None
                    else product_supplier.purchase_price
                ),
                quantity_unit_snapshot=product_supplier.product.quantity_unit,
                workspace_id=membership.workspace_id,
            )
        )

    db.add(restock)
    commit_or_raise(db)

    return db.scalars(
        select(Restock)
        .options(
            selectinload(Restock.lines)
            .selectinload(RestockLine.product_supplier)
            .selectinload(ProductSupplier.product),
            selectinload(Restock.lines)
            .selectinload(RestockLine.product_supplier)
            .selectinload(ProductSupplier.supplier),
        )
        .where(
            Restock.id == restock.id,
            Restock.workspace_id == membership.workspace_id,
        )
    ).one()
