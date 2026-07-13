from typing import Annotated

from fastapi import APIRouter, Query

from app.models import Tag
from app.schemas import PaginatedResponse, TagCreate, TagResponse
from app.tags import normalize_tag_name
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/tags", tags=["tags"])
