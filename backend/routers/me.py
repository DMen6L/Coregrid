from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import select

from app.models import WorkspaceInvitation, WorkspaceMembership
from app.schemas import WorkspaceInvitationResponse, WorkspaceResponse
from helpers.dependencies import CurrentUser, DbSession
from helpers.transactions import commit_or_raise
from helpers.update_helpers import check_unique_constraints


router = APIRouter(prefix="/me", tags=["me"])


@router.get(
    "/invitations",
    response_model=list[WorkspaceInvitationResponse],
    status_code=status.HTTP_200_OK,
)
def get_invitations(
    db: DbSession,
    current_user: CurrentUser,
):
    now = datetime.now()
    statement = select(WorkspaceInvitation).where(
        WorkspaceInvitation.email == current_user.email,
        WorkspaceInvitation.accepted_at.is_(None),
        WorkspaceInvitation.revoked_at.is_(None),
        WorkspaceInvitation.expires_at > now,
    )

    return db.scalars(statement).all()


@router.post(
    "/invitations/accept/{invitation_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
)
def accept_invitation(
    db: DbSession,
    current_user: CurrentUser,
    invitation_id: Annotated[UUID, Path()],
):
    invitation = db.scalar(
        select(WorkspaceInvitation).where(
            WorkspaceInvitation.id == invitation_id,
        )
    )
    now = datetime.now()

    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such invitation",
        )
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with such email cannot accept this invitation",
        )
    if invitation.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"invitation has expired at {invitation.expires_at}",
        )
    if invitation.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"invitation has been revoked at {invitation.revoked_at}",
        )
    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"invitation has been already accepted at {invitation.accepted_at}",
        )
    if (
        db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == invitation.workspace_id,
                WorkspaceMembership.user_id == current_user.id,
            )
        )
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of the invited workspace",
        )

    membership_schema = {
        "user_id": current_user.id,
        "workspace_id": invitation.workspace_id,
        "role": invitation.role,
    }

    check_unique_constraints(
        db=db,
        model=WorkspaceMembership,
        constraint_name="uq_workspace_memberships_user_workspace",
        values=membership_schema,
    )

    invitation.accepted_at = now

    membership = WorkspaceMembership(**membership_schema)

    db.add(membership)
    commit_or_raise(db)

    return {
        "id": membership.workspace_id,
        "name": membership.workspace.name,
        "role": membership.role,
    }
