from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field, model_validator, StringConstraints

# ======
# FIELDS
# ======

IIN = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^\d{12}$"),
]
Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
PhoneNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^\d{12}$"),
]

# ===============
# VALIDATOR CLASS
# ===============


class UpdateValidator(BaseModel):
    @model_validator(mode="after")
    def non_empty_fields(self):
        if not self.model_fields_set:
            raise ValueError("update models cannot be empty")
        return self


# =======
# SCHEMAS
# =======


class CompanyCreate(BaseModel):
    name: Name
    iin: IIN


class CompanyResponse(BaseModel):
    id: int
    name: str
    iin: str


class CompanyUpdate(UpdateValidator):
    name: Name | None = None
    iin: IIN | None = None


class SupplierCreate(BaseModel):
    name: Name
    phone_number: PhoneNumber


class SupplierResponse(BaseModel):
    id: int
    name: str
    phone_number: str


class SupplierUpdate(UpdateValidator):
    name: Name | None = None
    phone_number: PhoneNumber | None = None


class ProductCreate(BaseModel):
    name: Name
    price: int = Field(gt=0)
    quantity: int = Field(default=0, ge=0, validate_default=True)

    company_id: int | None = None
    supplier_id: int | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    price: int
    quantity: int
    created_at: datetime

    company_id: int | None
    supplier_id: int | None


class ProductUpdate(UpdateValidator):
    name: Name | None = None
    price: int | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=0, validate_default=True)

    company_id: int | None = None
    supplier_id: int | None = None
