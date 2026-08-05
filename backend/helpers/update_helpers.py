from collections.abc import Mapping, Sequence
from typing import cast


def build_unique_values_candidates(
    unique_fields: Sequence[str],
    update_data: Mapping[str, object],
    update_obj: object,
) -> tuple[dict[str, object], bool]:
    candidate_values: dict[str, object] = {}
    identity_changed = False

    for field in unique_fields:
        curr_val = cast(object, getattr(update_obj, field))

        if field in update_data:
            new_val = update_data[field]
        else:
            new_val = curr_val

        candidate_values[field] = new_val

        if new_val != curr_val:
            identity_changed = True

    return candidate_values, identity_changed
