from typing import Literal, TypeVar

from pydantic import BaseModel

from app.db import Base

OrmT = TypeVar("OrmT")
AggregateRowT = TypeVar("AggregateRowT", bound=tuple[object, ...])
ResponseT = TypeVar("ResponseT", bound=BaseModel)
OrmModelT = TypeVar("OrmModelT", bound=Base)

DEFAULT_QUANTITY_UNIT = "шт"
QUANTITY_UNIT_MAX_LENGTH = 20

BestSalesMode = Literal[
    "quantity",
    "revenue",
    "gross_profit",
]
