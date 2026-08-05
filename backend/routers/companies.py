from typing import Annotated, cast

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import Integer, func, select, type_coerce

from app.models import Company
from app.schemas import CompanyCreate, CompanyResponse, CompanyUpdate, PaginatedResponse
from helpers.dependencies import DbSession
from helpers.pagination import paginate
from helpers.transactions import commit_or_raise
from helpers.update_helpers import build_unique_values_candidates

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

    name_val, name_changed = build_unique_values_candidates(
        ("name",),
        update_data,
        company,
    )

    iin_val, iin_changed = build_unique_values_candidates(
        ("iin",),
        update_data,
        company,
    )

    if name_changed:
        candidate_name = cast(str, name_val["name"])

        duplicate_company_id = db.scalar(
            select(Company.id).where(
                Company.id != id,
                Company.name == candidate_name,
            )
        )

        if duplicate_company_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="company with this name exists.",
            )

    if iin_changed:
        candidate_iin = cast(str | None, iin_val["iin"])

        duplicate_company_id = db.scalar(
            select(Company.id).where(
                Company.id != id,
                Company.iin == candidate_iin,
            )
        )

        if duplicate_company_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="company with this iin exists.",
            )

    for field, value in update_data.items():
        setattr(company, field, value)

    commit_or_raise(db)
    db.refresh(company)

    return company
