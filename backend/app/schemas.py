from datetime import date, datetime
from typing import Annotated, Generic, Literal, TypeVar
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


class StockMovementLineCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity_delta: int

    @field_validator("quantity_delta")
    @classmethod
    def quantity_delta_cannot_be_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_delta cannot be zero")
        return value


class StockMovementCreate(BaseModel):
    movement_type: MovementType
    note: str | None = Field(default=None, max_length=500)
    lines: list[StockMovementLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lines(self):
        product_ids = [line.product_id for line in self.lines]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("movement lines cannot repeat product_id")

        if self.movement_type == "in":
            invalid_line = any(line.quantity_delta < 0 for line in self.lines)
            if invalid_line:
                raise ValueError("incoming movements must increase stock")

        if self.movement_type == "out":
            invalid_line = any(line.quantity_delta > 0 for line in self.lines)
            if invalid_line:
                raise ValueError("outgoing movements must decrease stock")

        return self


class StockMovementLineResponse(BaseModel):
    id: int
    product_id: int
    quantity_delta: int
    quantity_before: int
    quantity_after: int
    unit_price_snapshot: int | None
    quantity_unit_snapshot: str


class StockMovementResponse(BaseModel):
    id: int
    movement_type: MovementType
    note: str | None
    created_at: datetime
    lines: list[StockMovementLineResponse]


class SaleLineCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: int = Field(gt=0)


class SaleCreate(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    lines: list[SaleLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lines(self):
        product_ids = [line.product_id for line in self.lines]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("sale lines cannot repeat product_id")

        return self


class SaleResponse(BaseModel):
    id: int
    stock_movement_id: int
    note: str | None
    created_at: datetime
    revenue: int
    lines: list[StockMovementLineResponse]


class SummariesResponse(BaseModel):
    dashboard_sales_value: int
    dashboard_sales_count: int
    low_stock: int
    out_of_stock: int


class PaginatedResponse(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool
