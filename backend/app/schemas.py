from datetime import datetime
from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    iin: str = Field(min_length=12, max_length=12)


class CompanyResponse(BaseModel):
    id: int
    name: str
    iin: str


class SupplierCreate(BaseModel):
    name: str = Field(min_length=4, max_length=255)
    phone_number: str = Field(min_length=12, max_length=12)


class SupplierResponse(BaseModel):
    id: int
    name: str
    phone_number: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=4, max_length=255)
    price: int = Field(gt=0)

    company_id: int | None = None
    supplier_id: int | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    price: int
    created_at: datetime

    company_id: int | None
    supplier_id: int | None
