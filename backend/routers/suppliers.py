from fastapi import APIRouter, HTTPException

from app.models import Supplier
from app.schemas import (
    PaginatedResponse,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/suppliers", tags=["suppliers"])
