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
    data: Mapping[str, object],
    obj: object,
    constraint_name: str,
) -> None:
    constraints = get_unique_constraints(model)
    unique_fields = constraints[constraint_name]

    candidate_values, changed = build_unique_values_candidates(
        unique_fields,
        data,
        obj,
    )

    if not changed:
        return

    if any(value is None for value in candidate_values.values()):
        return

    conditions = []
    for field, value in candidate_values.items():
        column = cast(InstrumentedAttribute[object], getattr(model, field))
        conditions.append(column == value)

    id_column = cast(InstrumentedAttribute[object], getattr(model, "id"))
    obj_id = cast(object, getattr(obj, "id"))

    duplicate_id = db.scalar(
        select(id_column).where(
            id_column != obj_id,
            *conditions,
        )
    )

    if duplicate_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Violated unique constraint: {constraint_name}",
        )
