from datetime import date, datetime
from pickle import NONE
from typing import ClassVar, Generic, Literal
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.type_definitions import (
    DEFAULT_QUANTITY_UNIT,
    IIN,
    AssignableRoles,
    ItemT,
    Name,
    NormalizedEmail,
    PhoneNumber,
    QuantityUnit,
    StockStatus,
    StrongPassword,
    TagName,
)
from helpers.pricing import calculate_floor_price


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
    email: NormalizedEmail
    name: Name
    password: StrongPassword


class WorkspaceCreate(BaseModel):
    name: Name


class WorkspaceInvitationCreate(BaseModel):
    email: NormalizedEmail
    role: AssignableRoles


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


class AuditLogCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: int = Field(gt=0)
    actor_user_id: int = Field(gt=0)
    target_user_id: int | None = Field(default=None, gt=0)

    action: str = Field(min_length=1)

    entity_type: str = Field(min_length=1)
    entity_id: str | None = Field(default=None, min_length=1)
    entity_label: str | None = Field(default=None, min_length=1)

    changes: dict[str, object] = Field(default_factory=dict)
    extra_data: dict[str, object] = Field(default_factory=dict)


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


class ProductSupplierAtomicUpdate(UpdateValidator):
    id: int = Field(gt=0)
    purchase_price: int | None = Field(default=None, gt=0)
    margin_percent: int | None = Field(default=None, ge=0)
    sale_price: int | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def must_update_at_least_one_link_field(self):
        if self.model_fields_set <= {"id"}:
            raise ValueError("product supplier update cannot contain only id")
        return self

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


class ProductAtomicUpdate(UpdateValidator):
    name: Name | None = None
    company_id: int | None = Field(default=None, gt=0)
    tags: list[TagName] | None = None
    quantity_unit: QuantityUnit | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)
    product_links: list[ProductSupplierAtomicUpdate] | None = Field(
        default=None,
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_product_links(self):
        if self.product_links is None:
            return self

        link_ids = [link.id for link in self.product_links]
        if len(set(link_ids)) != len(link_ids):
            raise ValueError("product supplier link ids must be unique")
        return self


class UserUpdate(UpdateValidator):
    name: Name | None = None
    email: NormalizedEmail | None = None


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: StrongPassword


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
    email: EmailStr


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str


class WorkspaceMembershipSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str


class WorkspaceMembershipResponse(WorkspaceMembershipSummaryResponse):
    user_id: int


class WorkspaceInvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: int
    inviter_user_id: int | None
    email: EmailStr
    role: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None


class UserInvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: int
    workspace_name: str
    inviter_user_id: int | None
    inviter_user_name: str | None
    inviter_user_email: EmailStr | None
    role: str
    created_at: datetime
    accepted_at: datetime | None
    expires_at: datetime
    revoked_at: datetime | None


class MeResponse(BaseModel):
    user: UserResponse
    workspaces: list[WorkspaceResponse]
    invitations: list[UserInvitationResponse]


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    created_at: datetime

    actor_user_id: int | None
    actor_name: str | None
    actor_email: str | None

    target_user_id: int | None
    target_name: str | None
    target_email: EmailStr | None

    action: str

    entity_type: str
    entity_id: str | None
    entity_label: str | None

    changes: dict[str, object] | None
    extra_data: dict[str, object] | None


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
