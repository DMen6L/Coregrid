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
