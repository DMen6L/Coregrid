from typing import Literal, TypeVar

from pydantic import BaseModel

OrmT = TypeVar("OrmT")
AggregateRowT = TypeVar("AggregateRowT", bound=tuple[object, ...])
ResponseT = TypeVar("ResponseT", bound=BaseModel)

DEFAULT_QUANTITY_UNIT = "шт"
QUANTITY_UNIT_MAX_LENGTH = 20

BestSalesMode = Literal[
    "quantity",
    "revenue",
    "gross_profit",
]
