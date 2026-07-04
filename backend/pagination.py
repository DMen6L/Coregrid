from math import ceil
from typing import Annotated

from fastapi import Query


DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]


def paginate(query, page: int, page_size: int) -> dict[str, object]:
    total = query.order_by(None).count()
    pages = ceil(total / page_size) if total else 0
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
