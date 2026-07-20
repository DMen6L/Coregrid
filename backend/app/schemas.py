from datetime import date, datetime
from typing import Annotated, Any, Generic, Literal, TypeVar
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    StringConstraints,
)

from app.pricing import calculate_floor_price
from app.units import DEFAULT_QUANTITY_UNIT, QUANTITY_UNIT_MAX_LENGTH

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
    StringConstraints(strip_whitespace=True, pattern=r"^(8\d{10}|\+7\d{10})$"),
]
TagName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
QuantityUnit = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=QUANTITY_UNIT_MAX_LENGTH,
    ),
]
MovementType = Literal["in", "out", "adjustment"]
StockStatus = Literal["available", "low", "out"]

ItemT = TypeVar("ItemT")

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
    model_config = ConfigDict(from_attributes=True)
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
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone_number: str


class SupplierUpdate(UpdateValidator):
    name: Name | None = None
    phone_number: PhoneNumber | None = None


class TagCreate(BaseModel):
    name: TagName


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ProductCreate(BaseModel):
    name: Name
    purchase_price: int = Field(gt=0)
    margin_percent: int = Field(default=0, ge=0, validate_default=True)
    sale_price: int | None = Field(default=None, gt=0)
    quantity: int = Field(default=0, ge=0, validate_default=True)
    quantity_unit: QuantityUnit = Field(
        default=DEFAULT_QUANTITY_UNIT,
        validate_default=True,
    )
    low_stock_threshold: int = Field(default=5, ge=0, validate_default=True)

    company_id: int | None = None
    supplier_id: int | None = None
    tags: list[TagName] = Field(default_factory=list)

    @model_validator(mode="after")
    def sale_price_must_not_be_below_floor(self):
        if self.sale_price is None:
            return self

        floor_price = calculate_floor_price(
            self.purchase_price,
            self.margin_percent,
        )
        if self.sale_price < floor_price:
            raise ValueError("sale_price cannot be lower than floor_price")

        return self


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    purchase_price: int
    margin_percent: int
    floor_price: int
    sale_price: int
    quantity: int
    quantity_unit: str
    low_stock_threshold: int
    stock_status: StockStatus
    created_at: datetime

    company_id: int | None
    supplier_id: int | None
    company_name: str | None = None
    supplier_name: str | None = None
    tags: list[TagResponse] = Field(default_factory=list)


class ProductUpdate(UpdateValidator):
    name: Name | None = None
    purchase_price: int | None = Field(default=None, gt=0)
    margin_percent: int | None = Field(default=None, ge=0)
    sale_price: int | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=0, validate_default=True)
    quantity_unit: QuantityUnit | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)

    company_id: int | None = None
    supplier_id: int | None = None
    tags: list[TagName] | None = None


class RestockLineCreate(BaseModel):
    product_id: int = Field(gt=0)
    restock_quantity: int = Field(gt=0)
    unit_cost_snapshot: int | None = Field(
        default=None,
        ge=0,
    )
    quantity_unit_snapshot: str = Field(
        default=DEFAULT_QUANTITY_UNIT,
        min_length=1,
        max_length=QUANTITY_UNIT_MAX_LENGTH,
    )


class RestockCreate(BaseModel):
    note: str | None = Field(default=None, max_length=500)

    lines: list[RestockLineCreate] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_products(self) -> "RestockCreate":
        product_ids = [line.product_id for line in self.lines]

        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Each product may appear only once in a restock.")
        return self


class RestockLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    restock_quantity: int
    unit_cost_snapshot: int | None
    quantity_unit_snapshot: str


class RestockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note: str | None
    created_at: datetime
    lines: list[RestockLineResponse]


class SaleLineCreate(BaseModel):
    product_id: int = Field(gt=0)
    sale_quantity: int = Field(gt=0)


class SaleCreate(BaseModel):
    note: str | None = Field(default=None, max_length=500)

    lines: list[SaleLineCreate] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_products(self) -> "SaleCreate":
        product_ids = [line.product_id for line in self.lines]

        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Each product may appear only once in a sale.")
        return self


class SaleLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    sale_quantity: int
    unit_cost_snapshot: int
    unit_sale_price_snapshot: int
    quantity_unit_snapshot: str


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note: str | None
    created_at: datetime
    lines: list[SaleLineResponse]


class DailySalesResponse(BaseModel):
    date: date
    sales_value: int


class SummariesResponse(BaseModel):
    dashboard_sales_value: int
    dashboard_sales_count: int
    low_stock: int
    out_of_stock: int
    latest_sales: list[DailySalesResponse]


class PaginatedResponse(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool
