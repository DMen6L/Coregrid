from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User, WorkspaceMembership
from app.type_definitions import ROLE_PERMISSIONS, Permissions
from helpers.auth import decode_access_token


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]
bearer_scheme = HTTPBearer()


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> User:
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_workspace_membership(
    db: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[int, Path(gt=0)],
) -> WorkspaceMembership:
    membership = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this workspace",
        )

    return membership


def require_workspace_permission(
    permission: Permissions,
):
    def dependency(
        membership: Annotated[
            WorkspaceMembership,
            Depends(require_workspace_membership),
        ],
    ) -> WorkspaceMembership:
        if permission not in ROLE_PERMISSIONS.get(membership.role, set()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient workspace permission",
            )

        return membership

    return dependency
