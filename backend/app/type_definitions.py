from typing import Annotated, Literal, TypeAlias, TypeVar

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

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
WEAK_PASSWORDS = frozenset(
    {
        "123456789012",
        "adminadmin",
        "changeme",
        "letmein",
        "password",
        "password1",
        "password123",
        "qwertyuiop",
        "welcome",
        "welcome123",
    }
)


def normalize_email(email: str) -> str:
    return email.casefold()


def validate_password_strength(password: str) -> str:
    if password != password.strip():
        raise ValueError("password cannot start or end with whitespace")

    if any(ord(char) < 32 or ord(char) == 127 for char in password):
        raise ValueError("password cannot contain control characters")

    normalized_password = "".join(password.casefold().split())
    if normalized_password in WEAK_PASSWORDS:
        raise ValueError("password is too common")

    if password.isdigit():
        raise ValueError("password cannot contain only digits")

    character_groups = [
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() and char != " " for char in password),
    ]

    if len(password) < 16 and sum(character_groups) < 3:
        raise ValueError(
            "passwords under 16 characters must include at least three of: "
            "lowercase letters, uppercase letters, digits, symbols"
        )

    return password


# Types
OrmT = TypeVar("OrmT")
AggregateRowT = TypeVar("AggregateRowT", bound=tuple[object, ...])
ResponseT = TypeVar("ResponseT", bound=BaseModel)
OrmModelT = TypeVar("OrmModelT", bound=Base)

ItemT = TypeVar("ItemT")

BestSalesMode: TypeAlias = Literal[
    "quantity",
    "revenue",
    "gross_profit",
]

StockStatus: TypeAlias = Literal["available", "low", "out"]

Permissions: TypeAlias = Literal[
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

IIN: TypeAlias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^\d{12}$"),
]
Name: TypeAlias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
PhoneNumber: TypeAlias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^(8\d{10}|\+7\d{10})$"),
]
TagName: TypeAlias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
QuantityUnit: TypeAlias = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=QUANTITY_UNIT_MAX_LENGTH,
    ),
]
NormalizedEmail: TypeAlias = Annotated[
    EmailStr,
    Field(max_length=254),
    AfterValidator(normalize_email),
]
StrongPassword: TypeAlias = Annotated[
    str,
    Field(min_length=12, max_length=128),
    AfterValidator(validate_password_strength),
]
