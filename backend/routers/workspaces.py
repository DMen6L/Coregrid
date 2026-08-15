from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Integer, func, select, type_coerce
from sqlalchemy.sql.functions import coalesce

from app.models import AuditLog, Workspace, WorkspaceMembership
from app.schemas import (
    AuditLogCreate,
    AuditLogResponse,
    PaginatedResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)
from helpers.dependencies import (
    CurrentUser,
    DbSession,
    require_workspace_membership,
    require_workspace_permission,
)
from helpers.pagination import paginate
from helpers.transactions import commit_or_raise, flush_or_raise, record_audit_log
from helpers.update_helpers import check_unique_constraints


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
)
def get_workspace_by_id(
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_membership),
    ],
):
    return {
        "id": membership.workspace_id,
        "name": membership.workspace.name,
        "role": membership.role,
    }


@router.get(
    "/{workspace_id}/logs",
    response_model=PaginatedResponse[AuditLogResponse],
    status_code=status.HTTP_200_OK,
)
def get_workspace_logs(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("workspace.manage")),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    statement = (
        select(AuditLog)
        .where(AuditLog.workspace_id == membership.workspace_id)
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
    )
    count_statement = select(type_coerce(func.count(AuditLog.id), Integer)).where(
        AuditLog.workspace_id == membership.workspace_id
    )

    return paginate(
        db=db,
        statement=statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=AuditLogResponse,
    )


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_workspace(
    db: DbSession,
    current_user: CurrentUser,
    workspace_data: WorkspaceCreate,
):
    workspace_schema = workspace_data.model_dump()

    check_unique_constraints(
        db=db,
        model=Workspace,
        constraint_name="uq_workspaces_name",
        values=workspace_schema,
    )

    workspace = Workspace(**workspace_schema)

    db.add(workspace)
    flush_or_raise(db)

    membership_schema = {
        "user_id": current_user.id,
        "workspace_id": workspace.id,
        "role": "owner",
    }

    check_unique_constraints(
        db=db,
        model=WorkspaceMembership,
        constraint_name="uq_workspace_memberships_user_workspace",
        values=membership_schema,
    )

    membership = WorkspaceMembership(**membership_schema)

    db.add(membership)

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            target_user_id=current_user.id,
            action="workspace.created",
            entity_type="workspace",
            entity_id=str(workspace.id),
            entity_label=workspace.name,
            extra_data={
                "owner_name": current_user.name,
                "owner_email": current_user.email,
            },
        ),
    )

    commit_or_raise(db)

    return {
        "id": membership.workspace_id,
        "name": membership.workspace.name,
        "role": membership.role,
    }
