from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.models import Product, Sale, StockMovement, StockMovementLine
from app.schemas import (
    PaginatedResponse,
    StockMovementCreate,
    StockMovementResponse,
    StockMovementSalesSummaryResponse,
)
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(tags=["stock movements"])
