from typing import Literal

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload

from app.models import Product, Sale, StockMovement, StockMovementLine
from app.schemas import PaginatedResponse, SaleCreate, SaleResponse
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/sales", tags=["sales"])
