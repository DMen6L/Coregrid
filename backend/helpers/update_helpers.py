from collections.abc import Mapping, Sequence
from typing import cast

from fastapi import HTTPException, status
from sqlalchemy import Table, UniqueConstraint, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.type_definitions import OrmModelT


def get_unique_constraints(model: type[OrmModelT]) -> dict[str, tuple[str, ...]]:
    table = cast(Table, model.__table__)
    unique_constraints: dict[str, tuple[str, ...]] = {}

    for constraint in table.constraints:
        if not isinstance(constraint, UniqueConstraint):
            continue

        constraint_name = constraint.name
        if constraint_name is None:
            continue

        unique_constraints[str(constraint_name)] = tuple(
            str(column.key) for column in constraint.columns
        )

    return unique_constraints


def build_unique_values_candidates(
    unique_fields: Sequence[str],
    data: Mapping[str, object],
    obj: object,
) -> tuple[dict[str, object], bool]:
    candidate_values: dict[str, object] = {}
    identity_changed = False

    for field in unique_fields:
        curr_val = cast(object, getattr(obj, field))

        if field in data:
            new_val = data[field]
        else:
            new_val = curr_val

        candidate_values[field] = new_val

        if new_val != curr_val:
            identity_changed = True

    return candidate_values, identity_changed


def check_unique_constraints(
    db: Session,
    model: type[OrmModelT],
    constraint_name: str,
    values: Mapping[str, object],
    exclude_id: int | None = None,
) -> None:
    constraints = get_unique_constraints(model)
    unique_fields = constraints[constraint_name]

    candidate_values = {field: values[field] for field in unique_fields}

    if any(value is None for value in candidate_values.values()):
        return

    conditions = [
        getattr(model, field) == value for field, value in candidate_values.items()
    ]

    model_id = cast(InstrumentedAttribute[object], getattr(model, "id"))
    statement = select(model_id).where(*conditions)

    if exclude_id is not None:
        statement = statement.where(model_id != exclude_id)

    duplicate_id = db.scalar(statement)

    if duplicate_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Violated unique constraint: {constraint_name}",
        )


def validate_update(
    db: Session,
    model: type[OrmModelT],
    constraint_name: str,
    update_data: Mapping[str, object],
    update_obj: object,
) -> None:
    unique_fields = get_unique_constraints(model)[constraint_name]

    candidate_values, changed = build_unique_values_candidates(
        unique_fields,
        update_data,
        update_obj,
    )

    exclude_id = cast(int, getattr(update_obj, "id"))

    if changed:
        check_unique_constraints(
            db,
            model,
            constraint_name,
            candidate_values,
            exclude_id=exclude_id,
        )


def password_must_not_include_identity(
    password: str,
    email: str,
    name: str,
) -> None:
    password = password.casefold()
    email_local_part = email.split("@", 1)[0].casefold()
    name = name.casefold()

    if email_local_part and email_local_part in password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="password cannot include email parts",
        )

    if name and name in password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="password cannot include name parts",
        )
