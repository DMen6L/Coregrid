from typing import Literal, TypeAlias, TypeVar

from pydantic import BaseModel

from app.db import Base

# Const vars
DEFAULT_QUANTITY_UNIT = "шт"
QUANTITY_UNIT_MAX_LENGTH = 20
ROLE_PERMISSIONS = {
    "owner": {
        "inventory.read",
        "catalog.write",
        "stock_movement.create",
        "members.manage",
        "workspace.manage",
        "workspace.delete",
    },
    "admin": {
        "inventory.read",
        "catalog.write",
        "stock_movement.create",
        "members.manage",
        "workspace.manage",
    },
    "manager": {
        "inventory.read",
        "catalog.write",
        "stock_movement.create",
    },
    "operator": {
        "inventory.read",
        "stock_movement.create",
    },
    "viewer": {
        "inventory.read",
    },
}

# Types
OrmT = TypeVar("OrmT")
AggregateRowT = TypeVar("AggregateRowT", bound=tuple[object, ...])
ResponseT = TypeVar("ResponseT", bound=BaseModel)
OrmModelT = TypeVar("OrmModelT", bound=Base)

BestSalesMode = Literal[
    "quantity",
    "revenue",
    "gross_profit",
]

Permissions = Literal[
    "inventory.read",
    "catalog.write",
    "stock_movement.create",
    "members.manage",
    "workspace.manage",
    "workspace.delete",
]

Roles: TypeAlias = Literal[
    "owner",
    "admin",
    "manager",
    "operator",
    "viewer",
]
