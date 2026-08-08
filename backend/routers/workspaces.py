from fastapi import APIRouter, status
from sqlalchemy import select

from app.models import Workspace, WorkspaceMembership
from app.schemas import WorkspaceResponse
from helpers.dependencies import CurrentUser, DbSession


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get(
    "",
    response_model=list[WorkspaceResponse],
    status_code=status.HTTP_200_OK,
)
def get_current_workspace(
    db: DbSession,
    current_user: CurrentUser,
):
    statement = (
        select(Workspace)
        .join(WorkspaceMembership)
        .where(WorkspaceMembership.user_id == current_user.id)
        .order_by(Workspace.name)
    )

    return db.scalars(statement).all()
