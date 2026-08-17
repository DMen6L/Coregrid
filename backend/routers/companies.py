from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import Integer, func, or_, select, type_coerce

from app.models import Company, WorkspaceMembership
from app.schemas import (
    AuditLogCreate,
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    PaginatedResponse,
)
from helpers.dependencies import (
    DbSession,
    require_workspace_permission,
)
from helpers.pagination import paginate
from helpers.transactions import commit_or_raise, flush_or_raise, record_audit_log
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
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("inventory.read")),
    ],
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
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
)
def get_company_by_id(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("inventory.read")),
    ],
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
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("catalog.write")),
    ],
    company_data: CompanyCreate,
) -> Company:
    company_schema = company_data.model_dump()
    company_schema["workspace_id"] = membership.workspace_id

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

    company = Company(**company_schema)

    db.add(company)
    flush_or_raise(db)

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            action="company.created",
            entity_type="company",
            entity_id=str(company.id),
            entity_label=company.name,
        ),
    )

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
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("catalog.write")),
    ],
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

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Empty update bodies cannot be processed",
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

    changes: dict[str, object] = {}

    for field, value in update_data.items():
        old_value = getattr(company, field)

        if old_value == value:
            continue

        changes[field] = {
            "old": old_value,
            "new": value,
        }
        setattr(company, field, value)

    if changes:
        record_audit_log(
            db=db,
            audit_log_data=AuditLogCreate(
                workspace_id=membership.workspace_id,
                actor_user_id=membership.user_id,
                action="company.updated",
                entity_type="company",
                entity_id=str(company.id),
                entity_label=company.name,
                changes=changes,
            ),
        )

    commit_or_raise(db)
    db.refresh(company)

    return company
