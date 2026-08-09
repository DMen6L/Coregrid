from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select

from app.models import Product, Tag, WorkspaceMembership
from app.schemas import PaginatedResponse, TagSummaryResponse
from helpers.dependencies import (
    DbSession,
    require_workspace_permission,
)
from helpers.pagination import aggr_paginate
from helpers.transactions import commit_or_raise

router = APIRouter(prefix="/workspaces/{workspace_id}/tags", tags=["tags"])


@router.get(
    "",
    response_model=PaginatedResponse[TagSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_tags_by_name(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("inventory.read")),
    ],
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
        .where(Tag.workspace_id == membership.workspace_id)
        .join(Tag.products)
        .group_by(Tag.id)
        .order_by(usage_count.desc(), Tag.name.asc())
    )
    count_statement = (
        select(func.count(Tag.id))
        .select_from(Tag)
        .where(Tag.workspace_id == membership.workspace_id)
    )

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
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_tag(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("catalog.write")),
    ],
    tag_id: Annotated[int, Path(gt=0)],
) -> None:
    tag = db.scalar(
        select(Tag).where(
            Tag.id == tag_id,
            Tag.workspace_id == membership.workspace_id,
        )
    )

    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag with that id is not found.",
        )

    db.delete(tag)
    commit_or_raise(db)
