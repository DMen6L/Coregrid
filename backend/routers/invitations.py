from datetime import datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select

from app.models import User, WorkspaceInvitation, WorkspaceMembership
from app.schemas import WorkspaceInvitationCreate, WorkspaceInvitationResponse
from helpers.dependencies import DbSession, require_workspace_permission
from helpers.transactions import commit_or_raise
from helpers.update_helpers import check_unique_constraints


router = APIRouter(
    prefix="/workspaces/{workspace_id}/invitations", tags=["invitations"]
)


@router.get(
    "",
    response_model=list[WorkspaceInvitationResponse],
    status_code=status.HTTP_200_OK,
)
def get_invitations(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("members.manage")),
    ],
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
):
    statement = select(WorkspaceInvitation).where(
        WorkspaceInvitation.workspace_id == membership.workspace_id
    )

    if search is not None:
        condition = WorkspaceInvitation.email.ilike(f"%{search}%")
        statement = statement.where(condition)

    return db.scalars(statement).all()


@router.post(
    "",
    response_model=WorkspaceInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_invitation(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("members.manage")),
    ],
    invite_data: WorkspaceInvitationCreate,
) -> WorkspaceInvitation:
    now = datetime.now()
    if (
        db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user.has(User.email == invite_data.email),
                WorkspaceMembership.workspace_id == membership.workspace_id,
            )
        )
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invited user is already in the workspace",
        )
    if (
        db.scalar(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.email == invite_data.email,
                WorkspaceInvitation.workspace_id == membership.workspace_id,
                WorkspaceInvitation.expires_at > now,
                WorkspaceInvitation.accepted_at.is_(None),
                WorkspaceInvitation.revoked_at.is_(None),
            )
        )
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation for the user for this workspace already exists",
        )

    raw_token = token_urlsafe(32)
    token_hash = sha256(raw_token.encode()).hexdigest()

    workspace_invitation_schema = invite_data.model_dump()
    workspace_invitation_schema["token_hash"] = token_hash

    check_unique_constraints(
        db=db,
        model=WorkspaceInvitation,
        constraint_name="uq_workspace_invitations_token_hash",
        values=workspace_invitation_schema,
    )

    expires_at = now + timedelta(days=7)

    workspace_invitation_schema["inviter_user_id"] = membership.user_id
    workspace_invitation_schema["workspace_id"] = membership.workspace_id
    workspace_invitation_schema["expires_at"] = expires_at

    workspace_invitation = WorkspaceInvitation(**workspace_invitation_schema)

    db.add(workspace_invitation)
    commit_or_raise(db)
    db.refresh(workspace_invitation)

    return workspace_invitation


@router.delete(
    "/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_invitation(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("members.manage")),
    ],
    invitation_id: Annotated[UUID, Path()],
) -> None:
    invitation = db.scalar(
        select(WorkspaceInvitation).where(
            WorkspaceInvitation.id == invitation_id,
            WorkspaceInvitation.accepted_at.is_(None),
            WorkspaceInvitation.workspace_id == membership.workspace_id,
        )
    )

    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending invitation with such id is not found",
        )

    db.delete(invitation)
    commit_or_raise(db)
