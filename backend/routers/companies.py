from typing import Annotated, cast

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import Integer, func, select, type_coerce

from app.models import Company
from app.schemas import CompanyCreate, CompanyResponse, CompanyUpdate, PaginatedResponse
from helpers.dependencies import DbSession
from helpers.pagination import paginate
from helpers.transactions import commit_or_raise
from helpers.update_helpers import (
    check_unique_constraints,
    validate_update,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get(
    "",
    response_model=PaginatedResponse[CompanyResponse],
    status_code=status.HTTP_200_OK,
)
def get_companies(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
):

    statement = select(Company).order_by(Company.id)
    count_statement = select(type_coerce(func.count(Company.id), Integer)).select_from(
        Company
    )

    if search and (search := search.strip()):
        condition = Company.name.ilike(f"%{search}%")

        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    return paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=CompanyResponse,
    )


@router.get("/{id}", response_model=CompanyResponse, status_code=status.HTTP_200_OK)
def get_company_by_id(db: DbSession, id: Annotated[int, Path(gt=0)]) -> Company:
    company = db.get(Company, id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company with this id does not exist.",
        )

    return company


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_company(db: DbSession, company_data: CompanyCreate):
    company = Company(**company_data.model_dump())

    db.add(company)
    commit_or_raise(db)
    db.refresh(company)

    return company


@router.patch(
    "/{id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
)
def patch_company(
    db: DbSession,
    patch_data: CompanyUpdate,
    id: Annotated[int, Path(gt=0)],
) -> Company:
    company = db.get(Company, id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company with this id does not exist.",
        )

    update_data = cast(
        dict[str, object],
        patch_data.model_dump(exclude_unset=True),
    )

    validate_update(
        db=db,
        model=Company,
        constraint_name="uq_companies_name",
        update_data=update_data,
        update_obj=company,
    )
    validate_update(
        db=db,
        model=Company,
        constraint_name="uq_companies_iin",
        update_data=update_data,
        update_obj=company,
    )

    for field, value in update_data.items():
        setattr(company, field, value)

    commit_or_raise(db)
    db.refresh(company)

    return company
