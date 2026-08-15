from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import ProductSupplier, Sale, SaleLine, WorkspaceMembership
from app.schemas import (
    AuditLogCreate,
    PaginatedResponse,
    SaleCreate,
    SaleResponse,
    SaleSummaryResponse,
)
from helpers.dependencies import (
    DbSession,
    require_workspace_permission,
)
from helpers.pagination import aggr_paginate
from helpers.transactions import commit_or_raise, flush_or_raise, record_audit_log


router = APIRouter(prefix="/workspaces/{workspace_id}/sales", tags=["sales"])


@router.get(
    "",
    response_model=PaginatedResponse[SaleSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_sales(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("inventory.read")),
    ],
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
        .where(Sale.workspace_id == membership.workspace_id)
        .join(Sale.lines)
        .group_by(Sale.id, Sale.note, Sale.created_at)
        .order_by(Sale.created_at.desc(), Sale.id.desc())
    )
    count_statement = (
        select(func.count(Sale.id))
        .select_from(Sale)
        .where(Sale.workspace_id == membership.workspace_id)
    )

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


@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
    status_code=status.HTTP_200_OK,
)
def get_sale_by_id(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("inventory.read")),
    ],
    sale_id: Annotated[int, Path(gt=0)],
):
    statement = (
        select(Sale)
        .options(
            selectinload(Sale.lines)
            .selectinload(SaleLine.product_supplier)
            .selectinload(ProductSupplier.product),
            selectinload(Sale.lines)
            .selectinload(SaleLine.product_supplier)
            .selectinload(ProductSupplier.supplier),
        )
        .where(
            Sale.id == sale_id,
            Sale.workspace_id == membership.workspace_id,
        )
    )

    sale = db.scalars(statement).one_or_none()

    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale with such id doesn't exist.",
        )

    return sale


@router.post("", response_model=SaleResponse, status_code=201)
def add_sale(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("stock_movement.create")),
    ],
    sale_data: SaleCreate,
) -> Sale:
    product_supplier_ids = {line.product_supplier_id for line in sale_data.lines}

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

    sale = Sale(
        note=sale_data.note,
        workspace_id=membership.workspace_id,
    )

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
                workspace_id=membership.workspace_id,
            )
        )

    db.add(sale)
    flush_or_raise(db)

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            action="sale.created",
            entity_type="sale",
            entity_id=str(sale.id),
            entity_label=f"Restock #{sale.id}",
            extra_data={
                "restock_lines": len(sale.lines),
                "total_quantity": sum(line.sale_quantity for line in sale.lines),
                "total_cost": sum(
                    line.sale_quantity * line.unit_cost_snapshot for line in sale.lines
                ),
                "note": sale.note,
            },
        ),
    )

    commit_or_raise(db)

    return db.scalars(
        select(Sale)
        .options(
            selectinload(Sale.lines)
            .selectinload(SaleLine.product_supplier)
            .selectinload(ProductSupplier.product),
            selectinload(Sale.lines)
            .selectinload(SaleLine.product_supplier)
            .selectinload(ProductSupplier.supplier),
        )
        .where(
            Sale.id == sale.id,
            Sale.workspace_id == membership.workspace_id,
        )
    ).one()
