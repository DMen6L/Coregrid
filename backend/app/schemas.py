from datetime import date, datetime
from typing import Annotated, ClassVar, Generic, Literal, TypeVar
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
    StringConstraints,
)

from app.type_definitions import DEFAULT_QUANTITY_UNIT, QUANTITY_UNIT_MAX_LENGTH
from helpers.pricing import calculate_floor_price

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
StockStatus = Literal["available", "low", "out"]

ItemT = TypeVar("ItemT")

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

# ===============
# VALIDATOR CLASS
# ===============


class UpdateValidator(BaseModel):
    nullable_update_fields: ClassVar[set[str]] = set()

    @field_validator("*", mode="before")
    @classmethod
    def reject_null_fields(
        cls,
        value,
        info: ValidationInfo,
    ):
        if value is None and info.field_name not in cls.nullable_update_fields:
            raise ValueError("field cannot be null")
        return value

    @model_validator(mode="after")
    def non_empty_fields(self):
        if not self.model_fields_set:
            raise ValueError("update models cannot be empty")
        return self


# =======
# SCHEMAS
# =======

# ==============
# Create Schemas
# ==============


class CompanyCreate(BaseModel):
    name: Name
    iin: IIN | None = None


class SupplierCreate(BaseModel):
    name: Name
    phone_number: PhoneNumber


class TagCreate(BaseModel):
    name: TagName


class ProductSupplierCreate(BaseModel):
    supplier_id: int = Field(gt=0)
    purchase_price: int = Field(gt=0)
    margin_percent: int = Field(default=0, ge=0, validate_default=True)
    sale_price: int | None = Field(default=None, gt=0)
    quantity: int = Field(default=0, ge=0, validate_default=True)

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


class ProductCreate(BaseModel):
    name: Name
    company_id: int = Field(gt=0)
    tags: list[TagName] = Field(default_factory=list)
    quantity_unit: QuantityUnit = Field(
        default=DEFAULT_QUANTITY_UNIT,
        validate_default=True,
    )
    low_stock_threshold: int = Field(default=5, ge=0, validate_default=True)


class RestockLineCreate(BaseModel):
    product_supplier_id: int = Field(gt=0)
    restock_quantity: int = Field(gt=0)
    unit_cost_snapshot: int | None = Field(
        default=None,
        ge=0,
    )


class RestockCreate(BaseModel):
    note: str | None = Field(default=None, max_length=500)

    lines: list[RestockLineCreate] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_product_suppliers(self) -> "RestockCreate":
        product_supplier_ids = [line.product_supplier_id for line in self.lines]

        if len(product_supplier_ids) != len(set(product_supplier_ids)):
            raise ValueError(
                "Each product-supplier link may appear only once in a restock."
            )
        return self


class SaleLineCreate(BaseModel):
    product_supplier_id: int = Field(gt=0)
    sale_quantity: int = Field(gt=0)


class SaleCreate(BaseModel):
    note: str | None = Field(default=None, max_length=500)

    lines: list[SaleLineCreate] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_product_suppliers(self) -> "SaleCreate":
        product_supplier_ids = [line.product_supplier_id for line in self.lines]

        if len(product_supplier_ids) != len(set(product_supplier_ids)):
            raise ValueError(
                "Each product-supplier link may appear only once in a sale."
            )
        return self


class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=254)
    name: Name
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: str) -> str:
        return email.casefold()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
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

    @model_validator(mode="after")
    def password_must_not_include_identity(self):
        password = self.password.casefold()
        email_local_part = self.email.split("@", 1)[0].casefold()
        name = self.name.casefold()

        if email_local_part and email_local_part in password:
            raise ValueError("password cannot contain the email username")

        if name and name in password:
            raise ValueError("password cannot contain the user's name")

        return self


# =====================
# Atomic create schemas
# =====================


class ProductSupplierAtomicCreate(BaseModel):
    supplier_id: int | None = Field(default=None, gt=0)
    supplier: SupplierCreate | None = Field(default=None)

    purchase_price: int = Field(gt=0)
    margin_percent: int = Field(default=0, ge=0, validate_default=True)
    sale_price: int | None = Field(default=None, gt=0)
    quantity: int = Field(default=0, ge=0, validate_default=True)

    @model_validator(mode="after")
    def validate_supplier_source(self):
        if (self.supplier is None) == (self.supplier_id is None):
            raise ValueError("Provide exactly one of supplier id or supplier")
        return self

    @model_validator(mode="after")
    def validate_sale_price(self):
        if self.sale_price is None:
            return self

        floor_price = calculate_floor_price(
            self.purchase_price,
            self.margin_percent,
        )
        if self.sale_price < floor_price:
            raise ValueError("sale_price cannot be lower than floor_price")

        return self


class ProductAtomicCreate(BaseModel):
    product_name: Name
    tags: list[TagName] = Field(default_factory=list)
    quantity_unit: QuantityUnit = Field(
        default=DEFAULT_QUANTITY_UNIT,
        validate_default=True,
    )
    low_stock_threshold: int = Field(default=5, ge=0, validate_default=True)

    # Company is either existing or needs to be created
    # Only one can be true
    company_id: int | None = Field(default=None, gt=0)
    company: CompanyCreate | None = Field(default=None)

    product_links: list[ProductSupplierAtomicCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_company_source(self):
        if (self.company is None) == (self.company_id is None):
            raise ValueError("Provide exactly one of company id or company")
        return self


# ==============
# Update schemas
# ==============


class CompanyUpdate(UpdateValidator):
    nullable_update_fields: ClassVar[set[str]] = {"iin"}

    name: Name | None = None
    iin: IIN | None = None


class SupplierUpdate(UpdateValidator):
    name: Name | None = None
    phone_number: PhoneNumber | None = None


class ProductUpdate(UpdateValidator):
    name: Name | None = None
    company_id: int | None = Field(default=None, gt=0)
    tags: list[TagName] | None = None
    quantity_unit: QuantityUnit | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)


class ProductSupplierUpdate(UpdateValidator):
    supplier_id: int | None = Field(default=None, gt=0)
    purchase_price: int | None = Field(default=None, gt=0)
    margin_percent: int | None = Field(default=None, ge=0)
    sale_price: int | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def sale_price_must_not_be_below_floor_if_possible(self):
        if (
            self.sale_price is None
            or self.purchase_price is None
            or self.margin_percent is None
        ):
            return self

        floor_price = calculate_floor_price(
            self.purchase_price,
            self.margin_percent,
        )
        if self.sale_price < floor_price:
            raise ValueError("sale_price cannot be lower than floor_price")

        return self


# Response schemas


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    iin: str | None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone_number: str
    product_links: list[ProductSupplierResponse]


class SupplierSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone_number: str
    product_links_count: int = Field(default=0, ge=0)


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TagSummaryResponse(TagResponse):
    usage_count: int


class ProductSupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    supplier_id: int
    product_name: str | None = None
    supplier_name: str | None = None
    purchase_price: int
    margin_percent: int
    floor_price: int
    sale_price: int
    quantity: int
    stock_status: StockStatus


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime

    company_id: int
    company_name: str
    quantity_unit: str
    low_stock_threshold: int
    tags: list[TagResponse] = Field(default_factory=list)
    supplier_links: list[ProductSupplierResponse] = Field(default_factory=list)


class ProductSummaryResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    quantity_unit: str
    low_stock_threshold: int = Field(default=5, ge=0)
    company_name: str
    tags: list[str] = Field(default_factory=list)

    suppliers_count: int
    total_quantity: int = Field(default=0, ge=0)
    min_purchase_price: int | None = None
    margin_percent: int | None = None
    min_sale_price: int | None = None
    stock_status: StockStatus


class RestockLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_supplier_id: int
    product_id: int
    product_name: str
    supplier_id: int
    supplier_name: str | None = None
    restock_quantity: int
    unit_cost_snapshot: int
    quantity_unit_snapshot: str


class RestockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note: str | None
    created_at: datetime
    lines: list[RestockLineResponse]


class RestockSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note: str | None
    created_at: datetime
    costs: int
    lines_count: int


class SaleLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_supplier_id: int
    product_id: int
    product_name: str
    supplier_id: int
    supplier_name: str
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


class SaleSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note: str | None
    created_at: datetime
    revenue: int
    lines_count: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str


# Other Response Schemas


class DailySalesResponse(BaseModel):
    date: date
    sales_value: int


class TopProduct(BaseModel):
    product_id: int
    product_name: str
    metric: int = Field(default=0, ge=0)


class TopSupplier(BaseModel):
    supplier_id: int
    supplier_name: str
    supplied_products: int


class SummariesResponse(BaseModel):
    dashboard_sales_value: int
    dashboard_sales_count: int
    low_stock: int
    out_of_stock: int
    latest_sales: list[DailySalesResponse]
    top_products: list[TopProduct]
    top_suppliers: list[TopSupplier]


class PaginatedResponse(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


# Auth Schemas


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
