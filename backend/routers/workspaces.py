from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Workspace, WorkspaceMembership
from app.schemas import WorkspaceCreate, WorkspaceResponse
from helpers.dependencies import CurrentUser, DbSession, require_workspace_membership
from helpers.transactions import commit_or_raise, flush_or_raise
from helpers.update_helpers import check_unique_constraints


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get(
    "",
    response_model=list[WorkspaceResponse],
    status_code=status.HTTP_200_OK,
)
def get_workspaces(
    db: DbSession,
    current_user: CurrentUser,
):
    statement = (
        select(WorkspaceMembership)
        .options(selectinload(WorkspaceMembership.workspace))
        .where(WorkspaceMembership.user_id == current_user.id)
    )

    return [
        {
            "id": membership.workspace_id,
            "name": membership.workspace.name,
            "role": membership.role,
        }
        for membership in db.scalars(statement).all()
    ]


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
)
def get_workspace_by_id(
    membership: Annotated[WorkspaceMembership, Depends(require_workspace_membership)],
):
    return {
        "id": membership.workspace_id,
        "name": membership.workspace.name,
        "role": membership.role,
    }


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
    commit_or_raise(db)

    return {
        "id": membership.workspace_id,
        "name": membership.workspace.name,
        "role": membership.role,
    }
