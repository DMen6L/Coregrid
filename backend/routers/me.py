from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import select

from app.models import User, WorkspaceInvitation, WorkspaceMembership
from app.schemas import (
    AuditLogCreate,
    MeResponse,
    UserPasswordUpdate,
    UserUpdate,
    WorkspaceResponse,
)
from helpers.auth import hash_password, verify_password
from helpers.dependencies import CurrentUser, DbSession
from helpers.services import get_user_info
from helpers.transactions import commit_or_raise, flush_or_raise, record_audit_log
from helpers.update_helpers import (
    check_unique_constraints,
    password_must_not_include_identity,
    validate_update,
)


router = APIRouter(prefix="/me", tags=["me"])


@router.get(
    "",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
)
def get_me(
    db: DbSession,
    current_user: CurrentUser,
):
    return get_user_info(
        db=db,
        user=current_user,
    )


@router.post(
    "/accept/{invitation_id}",
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
            detail="No invitation with provided id",
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
    flush_or_raise(db)

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            target_user_id=membership.user_id,
            action="member.created",
            entity_type="member",
            entity_id=str(membership.id),
            entity_label=current_user.email,
            extra_data={
                "email": invitation.email,
                "role": invitation.role,
                "accepted_at": now.isoformat(),
            },
        ),
    )

    commit_or_raise(db)

    return {
        "id": membership.workspace_id,
        "name": membership.workspace.name,
        "role": membership.role,
    }


@router.patch(
    "",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
)
def patch_me(
    db: DbSession,
    current_user: CurrentUser,
    user_data: UserUpdate,
):
    user_schema = user_data.model_dump(exclude_unset=True)

    validate_update(
        db=db,
        model=User,
        constraint_name="uq_users_email",
        update_data=user_schema,
        update_obj=current_user,
    )

    for field_name, value in user_schema.items():
        setattr(current_user, field_name, value)

    commit_or_raise(db)
    db.refresh(current_user)

    return get_user_info(
        db=db,
        user=current_user,
    )


@router.patch(
    "/password",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
)
def patch_password(
    db: DbSession,
    current_user: CurrentUser,
    password_data: UserPasswordUpdate,
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current written password is incorrect",
        )
    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords cannot repeat themselves",
        )
    password_must_not_include_identity(
        password=password_data.new_password,
        email=current_user.email,
        name=current_user.name,
    )

    current_user.password_hash = hash_password(password_data.new_password)

    commit_or_raise(db)
    db.refresh(current_user)

    return get_user_info(
        db=db,
        user=current_user,
    )


@router.delete(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def leave_workspace(
    db: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[int, Path(gt=0)],
) -> None:
    membership = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == current_user.id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not part of this workspace",
        )
    if membership.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner has to transfer ownership before leaving the workspace",
        )

    left_at = datetime.now()

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            target_user_id=membership.user_id,
            action="member.left",
            entity_type="member",
            entity_id=str(membership.id),
            entity_label=current_user.email,
            extra_data={
                "email": current_user.email,
                "role": membership.role,
                "left_at": left_at.isoformat(),
            },
        ),
    )

    db.delete(membership)

    commit_or_raise(db)
