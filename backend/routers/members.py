from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import Integer, func, or_, select, type_coerce

from app.models import User, WorkspaceMembership
from app.schemas import (
    AuditLogCreate,
    PaginatedResponse,
    WorkspaceMembershipResponse,
    WorkspaceMembershipSummaryResponse,
)
from app.type_definitions import AssignableRoles
from helpers.dependencies import DbSession, require_workspace_permission
from helpers.pagination import aggr_paginate
from helpers.transactions import commit_or_raise, record_audit_log


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
            detail="Member with given id is not found",
        )

    return WorkspaceMembershipResponse.model_validate(dict(result))


@router.patch(
    "/{member_id}/role",
    response_model=WorkspaceMembershipResponse,
    status_code=status.HTTP_200_OK,
)
def change_member_role(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("members.manage")),
    ],
    member_id: Annotated[int, Path(gt=0)],
    new_role: Annotated[AssignableRoles, Query()],
) -> WorkspaceMembershipResponse:
    member = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == membership.workspace_id,
            WorkspaceMembership.id == member_id,
        )
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member with given id is not found",
        )
    if member.id == membership.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update your own role within the workspace",
        )
    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change owner role, use dedicated endpoint",
        )
    if new_role == "admin" and membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner can grant admin",
        )
    if member.role == "admin" and membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner can change admins",
        )
    if member.role == new_role:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The member roles cannot be the same after the update",
        )

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            target_user_id=member.user_id,
            action="member.role_updated",
            entity_type="member",
            entity_id=str(member.id),
            entity_label=member.user.email,
            changes={
                "role": {
                    "old": member.role,
                    "new": new_role,
                }
            },
        ),
    )

    member.role = new_role

    commit_or_raise(db)

    result = (
        db.execute(
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
        .mappings()
        .one_or_none()
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member with given id is not found",
        )

    return WorkspaceMembershipResponse.model_validate(dict(result))


@router.delete(
    "/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_member(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("members.manage")),
    ],
    member_id: Annotated[int, Path(gt=0)],
) -> None:
    member = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == membership.workspace_id,
            WorkspaceMembership.id == member_id,
        )
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member with this id is not found",
        )
    if member.id == membership.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete yourself, use dedicated endpoint",
        )
    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner cannot be deleted",
        )
    if member.role == "admin" and membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner can delete admins",
        )

    deleted_at = datetime.now()

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            target_user_id=member.user_id,
            action="member.removed",
            entity_type="member",
            entity_id=str(member.id),
            entity_label=member.user.email,
            extra_data={
                "role": member.role,
                "deleted_at": deleted_at.isoformat(),
            },
        ),
    )

    db.delete(member)
    commit_or_raise(db)
