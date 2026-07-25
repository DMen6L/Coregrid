from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.models import Tag
from app.schemas import PaginatedResponse, TagCreate, TagResponse
from devs import DbSession
from errors import commit_or_raise
from utils import paginate

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=PaginatedResponse[TagResponse],
    status_code=status.HTTP_200_OK,
)
def get_tags_by_name(
    db: DbSession,
    search: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[TagResponse]:
    statement = select(Tag).order_by(Tag.id)
    count_statement = select(func.count(Tag.id)).select_from(Tag)

    if search and (search := search.strip()):
        condition = Tag.name.ilike(f"%{search}%")

        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    return paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=TagResponse,
    )
