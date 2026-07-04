from fastapi import APIRouter, HTTPException

from app.models import Company
from app.schemas import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    PaginatedResponse,
)
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse, status_code=201)
def add_company(company_data: CompanyCreate, db: DbSession) -> Company:
    new_company = Company(iin=company_data.iin, name=company_data.name)

    db.add(new_company)
    commit_or_raise(db)
    db.refresh(new_company)

    return new_company


@router.patch("/{id}", response_model=CompanyResponse, status_code=200)
def patch_company(id: int, update_data: CompanyUpdate, db: DbSession) -> Company:
    company = db.get(Company, id)

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    changes = update_data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(company, field, value)

    commit_or_raise(db)
    db.refresh(company)

    return company


@router.get("", response_model=PaginatedResponse[CompanyResponse], status_code=200)
def get_companies(
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = DEFAULT_PAGE_SIZE,
) -> dict[str, object]:
    return paginate(db.query(Company).order_by(Company.id), page, page_size)


@router.get("/{id}", response_model=CompanyResponse, status_code=200)
def get_company(id: int, db: DbSession) -> Company:
    company = db.get(Company, id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


@router.delete("/{id}", status_code=204)
def delete_company(id: int, db: DbSession) -> None:
    company = db.get(Company, id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(company)
    commit_or_raise(db)
