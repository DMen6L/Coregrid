from fastapi import HTTPException
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def commit_or_raise(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        if isinstance(exc.orig, UniqueViolation):
            raise HTTPException(
                status_code=409, detail="Duplicate value conflicts existing row"
            ) from exc
        if isinstance(exc.orig, ForeignKeyViolation):
            raise HTTPException(
                status_code=409, detail="Referenced row does not exist or was changed"
            ) from exc
        if isinstance(exc.orig, CheckViolation):
            raise HTTPException(
                status_code=422, detail="Value violates a database constraint"
            ) from exc

        raise HTTPException(status_code=500, detail="Database error") from exc
