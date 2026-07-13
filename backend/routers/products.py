from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import selectinload

from app.models import Company, Product, Supplier, Tag
from app.pricing import calculate_floor_price
from app.schemas import (
    PaginatedResponse,
    ProductCreate,
    ProductResponse,
    ProductSummaryResponse,
    ProductUpdate,
    TagName,
)
from app.tags import get_or_create_tags, normalize_tag_name, normalize_tag_names
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/products", tags=["products"])
