from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Integer, func, select, type_coerce

from app.models import Supplier
from app.schemas import PaginatedResponse, SupplierCreate, SupplierResponse
from devs import DbSession
from errors import commit_or_raise
from utils import paginate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=PaginatedResponse[SupplierResponse], status_code=200)
def get_supplier_by_name(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    statement = select(Supplier).order_by(Supplier.id)
    count_statement = select(type_coerce(func.count(Supplier.id), Integer)).select_from(
        Supplier
    )

    if search and (search := search.strip()):
        condition = Supplier.name.ilike(f"%{search}%")

        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    return paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=SupplierResponse,
    )


@router.post("", response_model=SupplierResponse, status_code=201)
def add_supplier(db: DbSession, supplier_data: SupplierCreate):
    supplier = Supplier(**supplier_data.model_dump())

    db.add(supplier)
    commit_or_raise(db)
    db.refresh(supplier)

    return supplier
