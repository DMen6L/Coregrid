from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import Product, ProductSupplier, Supplier, WorkspaceMembership
from app.schemas import (
    PaginatedResponse,
    SupplierCreate,
    SupplierResponse,
    SupplierSummaryResponse,
    SupplierUpdate,
)
from helpers.dependencies import DbSession, require_workspace_membership
from helpers.pagination import aggr_paginate
from helpers.transactions import commit_or_raise
from helpers.update_helpers import (
    check_unique_constraints,
    validate_update,
)


router = APIRouter(prefix="/workspaces/{workspace_id}/suppliers", tags=["suppliers"])


@router.get(
    "",
    response_model=PaginatedResponse[SupplierSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_suppliers(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> PaginatedResponse[SupplierSummaryResponse]:
    statement = (
        select(
            Supplier.id.label("id"),
            Supplier.name.label("name"),
            Supplier.phone_number.label("phone_number"),
            func.count(ProductSupplier.id).label("product_links_count"),
        )
        .select_from(Supplier)
        .where(Supplier.workspace_id == membership.workspace_id)
        .outerjoin(Supplier.product_links)
        .group_by(Supplier.id)
        .order_by(Supplier.id)
    )
    count_statement = (
        select(func.count(Supplier.id))
        .select_from(Supplier)
        .where(Supplier.workspace_id == membership.workspace_id)
    )

    if search and (search := search.strip()):
        condition = Supplier.name.ilike(f"%{search}%")

        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    return aggr_paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=SupplierSummaryResponse,
    )


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    status_code=status.HTTP_200_OK,
)
def get_supplier_by_id(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    supplier_id: Annotated[int, Path(gt=0)],
) -> Supplier:
    statement = (
        select(Supplier)
        .options(
            selectinload(Supplier.product_links)
            .selectinload(ProductSupplier.product)
            .selectinload(Product.company),
        )
        .where(
            Supplier.id == supplier_id,
            Supplier.workspace_id == membership.workspace_id,
        )
    )

    supplier = db.scalars(statement).one_or_none()

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )

    return supplier


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_supplier(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    supplier_data: SupplierCreate,
) -> Supplier:
    supplier_schema = supplier_data.model_dump()
    supplier_schema["workspace_id"] = membership.workspace_id

    check_unique_constraints(
        db=db,
        model=Supplier,
        constraint_name="uq_suppliers_workspace_name",
        values=supplier_schema,
    )
    check_unique_constraints(
        db=db,
        model=Supplier,
        constraint_name="uq_suppliers_workspace_phone_number",
        values=supplier_schema,
    )

    supplier = Supplier(**supplier_schema)

    db.add(supplier)
    commit_or_raise(db)
    db.refresh(supplier)

    return supplier


@router.patch(
    "/{supplier_id}",
    response_model=SupplierResponse,
    status_code=status.HTTP_200_OK,
)
def patch_supplier(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    patch_data: SupplierUpdate,
    supplier_id: Annotated[
        int,
        Path(gt=0),
    ],
) -> Supplier:
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.workspace_id == membership.workspace_id,
        )
    )

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier with such id not found",
        )

    update_data = patch_data.model_dump(exclude_unset=True)
    update_data["workspace_id"] = membership.workspace_id

    validate_update(
        db=db,
        model=Supplier,
        constraint_name="uq_suppliers_workspace_name",
        update_data=update_data,
        update_obj=supplier,
    )
    validate_update(
        db=db,
        model=Supplier,
        constraint_name="uq_suppliers_workspace_phone_number",
        update_data=update_data,
        update_obj=supplier,
    )

    for field, value in update_data.items():
        setattr(supplier, field, value)

    commit_or_raise(db)
    db.refresh(supplier)

    return supplier
