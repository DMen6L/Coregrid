from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Integer, func, select, type_coerce

from app.models import Company
from app.schemas import CompanyCreate, CompanyResponse, PaginatedResponse
from devs import DbSession
from errors import commit_or_raise
from utils import paginate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=PaginatedResponse[CompanyResponse], status_code=200)
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


@router.post("", response_model=CompanyResponse, status_code=201)
def add_company(db: DbSession, company_data: CompanyCreate):
    company = Company(**company_data.model_dump())

    db.add(company)
    commit_or_raise(db)
    db.refresh(company)

    return company
