from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import Product, ProductSupplier, Supplier
from app.schemas import (
    PaginatedResponse,
    SupplierCreate,
    SupplierResponse,
    SupplierSummaryResponse,
    SupplierUpdate,
)
from helpers.dependencies import DbSession
from helpers.pagination import aggr_paginate
from helpers.transactions import commit_or_raise
from helpers.update_helpers import (
    check_unique_constraints,
)


router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get(
    "",
    response_model=PaginatedResponse[SupplierSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_suppliers(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    statement = (
        select(
            Supplier.id.label("id"),
            Supplier.name.label("name"),
            Supplier.phone_number.label("phone_number"),
            func.count(ProductSupplier.id).label("product_links_count"),
        )
        .select_from(Supplier)
        .outerjoin(Supplier.product_links)
        .group_by(Supplier.id)
        .order_by(Supplier.id)
    )
    count_statement = select(func.count(Supplier.id)).select_from(Supplier)

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
    "/{id}",
    response_model=SupplierResponse,
    status_code=status.HTTP_200_OK,
)
def get_supplier_by_id(
    db: DbSession,
    id: Annotated[int, Path(gt=0)],
) -> Supplier:
    statement = (
        select(Supplier)
        .options(
            selectinload(Supplier.product_links)
            .selectinload(ProductSupplier.product)
            .selectinload(Product.company),
        )
        .where(Supplier.id == id)
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
def add_supplier(db: DbSession, supplier_data: SupplierCreate):
    supplier = Supplier(**supplier_data.model_dump())

    db.add(supplier)
    commit_or_raise(db)
    db.refresh(supplier)

    return supplier


@router.patch(
    "/{id}",
    response_model=SupplierResponse,
    status_code=status.HTTP_200_OK,
)
def patch_supplier(
    db: DbSession, patch_data: SupplierUpdate, id: Annotated[int, Path(gt=0)]
) -> Supplier:
    supplier = db.get(Supplier, id)

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier with such id not found",
        )

    update_data = patch_data.model_dump(exclude_unset=True)

    check_unique_constraints(
        db,
        Supplier,
        update_data,
        supplier,
        "uq_suppliers_name",
    )
    check_unique_constraints(
        db,
        Supplier,
        update_data,
        supplier,
        "uq_suppliers_phone_number",
    )

    for field, value in update_data.items():
        setattr(supplier, field, value)

    commit_or_raise(db)
    db.refresh(supplier)

    return supplier
