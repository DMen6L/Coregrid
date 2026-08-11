from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import Integer, func, or_, select, type_coerce

from app.models import User, WorkspaceMembership
from app.schemas import (
    PaginatedResponse,
    WorkspaceMembershipResponse,
    WorkspaceMembershipSummaryResponse,
)
from helpers.dependencies import DbSession, require_workspace_permission
from helpers.pagination import aggr_paginate


router = APIRouter(prefix="/workspaces/{workspace_id}/members", tags=["members"])


@router.get(
    "",
    response_model=PaginatedResponse[WorkspaceMembershipSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_members(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("members.manage")),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> PaginatedResponse[WorkspaceMembershipSummaryResponse]:
    statement = (
        select(
            WorkspaceMembership.id.label("id"),
            User.name.label("name"),
            User.email.label("email"),
            WorkspaceMembership.role.label("role"),
        )
        .select_from(WorkspaceMembership)
        .where(WorkspaceMembership.workspace_id == membership.workspace_id)
        .join(WorkspaceMembership.user)
        .order_by(WorkspaceMembership.id)
    )
    count_statement = (
        select(type_coerce(func.count(WorkspaceMembership.user_id), Integer))
        .select_from(WorkspaceMembership)
        .join(WorkspaceMembership.user)
        .where(WorkspaceMembership.workspace_id == membership.workspace_id)
    )

    if search and (search := search.strip()):
        condition = or_(
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    return aggr_paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=WorkspaceMembershipSummaryResponse,
    )


@router.get(
    "/{member_id}",
    response_model=WorkspaceMembershipResponse,
    status_code=status.HTTP_200_OK,
)
def get_member_by_id(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("members.manage")),
    ],
    member_id: Annotated[int, Path(gt=0)],
) -> WorkspaceMembershipResponse:
    statement = (
        select(
            WorkspaceMembership.id.label("id"),
            User.name.label("name"),
            User.email.label("email"),
            WorkspaceMembership.role.label("role"),
            WorkspaceMembership.user_id.label("user_id"),
        )
        .select_from(WorkspaceMembership)
        .join(WorkspaceMembership.user)
        .where(
            WorkspaceMembership.id == member_id,
            WorkspaceMembership.workspace_id == membership.workspace_id,
        )
    )

    result = db.execute(statement).mappings().one_or_none()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return WorkspaceMembershipResponse.model_validate(dict(result))
