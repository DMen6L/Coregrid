from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from helpers.dependencies import DbSession


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
def health():
    return {"status": "ok"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
)
def ready(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": "error"},
        )

    return {"status": "ready", "database": "ok"}
