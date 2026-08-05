from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import func, select

from app.models import Product, Tag
from app.schemas import PaginatedResponse, TagSummaryResponse
from helpers.dependencies import DbSession
from helpers.pagination import aggr_paginate
from helpers.transactions import commit_or_raise

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=PaginatedResponse[TagSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_tags_by_name(
    db: DbSession,
    search: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[TagSummaryResponse]:
    usage_count = func.count(Product.id).label("usage_count")
    statement = (
        select(
            Tag.id.label(("id")),
            Tag.name.label("name"),
            usage_count,
        )
        .select_from(Tag)
        .join(Tag.products)
        .group_by(Tag.id)
        .order_by(usage_count.desc(), Tag.name.asc())
    )
    count_statement = select(func.count(Tag.id)).select_from(Tag)

    if search and (search := search.strip()):
        condition = Tag.name.ilike(f"%{search}%")

        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    return aggr_paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=TagSummaryResponse,
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_tag(db: DbSession, id: Annotated[int, Path(gt=0)]) -> None:
    tag = db.get(Tag, id)

    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag with that id is not found.",
        )

    db.delete(tag)
    commit_or_raise(db)
