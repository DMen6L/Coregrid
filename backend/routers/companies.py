from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import Integer, func, or_, select, type_coerce

from app.models import Company, WorkspaceMembership
from app.schemas import CompanyCreate, CompanyResponse, CompanyUpdate, PaginatedResponse
from helpers.dependencies import DbSession, require_workspace_membership
from helpers.pagination import paginate
from helpers.transactions import commit_or_raise
from helpers.update_helpers import (
    check_unique_constraints,
    validate_update,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/companies", tags=["companies"])


@router.get(
    "",
    response_model=PaginatedResponse[CompanyResponse],
    status_code=status.HTTP_200_OK,
)
def get_companies(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> PaginatedResponse[CompanyResponse]:
    statement = (
        select(Company)
        .order_by(Company.id)
        .where(Company.workspace_id == membership.workspace_id)
    )
    count_statement = (
        select(type_coerce(func.count(Company.id), Integer))
        .select_from(Company)
        .where(Company.workspace_id == membership.workspace_id)
    )

    if search and (search := search.strip()):
        condition = or_(
            Company.name.ilike(f"%{search}%"),
            Company.iin.ilike(f"%{search}%"),
        )

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


@router.get(
    "/{company_id}", response_model=CompanyResponse, status_code=status.HTTP_200_OK
)
def get_company_by_id(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    company_id: Annotated[int, Path(gt=0)],
) -> Company:
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.workspace_id == membership.workspace_id,
        )
    )

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
def add_company(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    company_data: CompanyCreate,
) -> Company:
    company_schema = company_data.model_dump()

    check_unique_constraints(
        db=db,
        model=Company,
        constraint_name="uq_companies_workspace_name",
        values=company_schema,
    )
    check_unique_constraints(
        db=db,
        model=Company,
        constraint_name="uq_companies_workspace_iin",
        values=company_schema,
    )

    company = Company(
        **company_schema,
        workspace_id=membership.workspace_id,
    )

    db.add(company)
    commit_or_raise(db)
    db.refresh(company)

    return company


@router.patch(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
)
def patch_company(
    db: DbSession,
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
    patch_data: CompanyUpdate,
    company_id: Annotated[int, Path(gt=0)],
) -> Company:
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.workspace_id == membership.workspace_id,
        )
    )
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
        constraint_name="uq_companies_workspace_name",
        update_data=update_data,
        update_obj=company,
    )
    validate_update(
        db=db,
        model=Company,
        constraint_name="uq_companies_workspace_iin",
        update_data=update_data,
        update_obj=company,
    )

    for field, value in update_data.items():
        setattr(company, field, value)

    commit_or_raise(db)
    db.refresh(company)

    return company
