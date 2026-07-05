from typing import Annotated

from fastapi import APIRouter, Query

from app.models import Tag
from app.schemas import PaginatedResponse, TagCreate, TagResponse
from app.tags import normalize_tag_name
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("", response_model=TagResponse, status_code=201)
def add_tag(tag_data: TagCreate, db: DbSession) -> Tag:
    new_tag = Tag(name=normalize_tag_name(tag_data.name))

    db.add(new_tag)
    commit_or_raise(db)
    db.refresh(new_tag)

    return new_tag


@router.get("", response_model=PaginatedResponse[TagResponse], status_code=200)
def get_tags(
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = DEFAULT_PAGE_SIZE,
    search: Annotated[str | None, Query(max_length=50)] = None,
) -> dict[str, object]:
    query = db.query(Tag)

    search_term = normalize_tag_name(search) if search else ""
    if search_term:
        query = query.filter(Tag.name.ilike(f"%{search_term}%"))

    return paginate(query.order_by(Tag.name), page, page_size)
