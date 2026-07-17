from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.schemas import PaginatedResponse


OrmT = TypeVar("OrmT")
ResponseT = TypeVar("ResponseT", bound=BaseModel)


def paginate(
    db: Session,
    statement: Select[tuple[OrmT]],
    count_statement: Select[tuple[int]],
    page: int,
    page_size: int,
    response_schema: type[ResponseT],
) -> PaginatedResponse[ResponseT]:
    total = db.execute(count_statement).scalar_one()

    paginated_statement = statement.offset((page - 1) * page_size).limit(page_size)

    records = db.scalars(paginated_statement).all()

    items = [response_schema.model_validate(record) for record in records]

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse[ResponseT](
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )
