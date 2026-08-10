from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    CheckConstraint,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from app.db import Base
from app.type_definitions import DEFAULT_QUANTITY_UNIT, QUANTITY_UNIT_MAX_LENGTH
from helpers.pricing import calculate_floor_price


# ======
# MODELS
# ======

product_tags = Table(
    "product_tags",
    Base.metadata,
    Column(
        "product_id",
        ForeignKey(
            "products.id",
            name="fk_product_tags_product_id_products",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey(
            "tags.id",
            name="fk_product_tags_tag_id_tags",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
)


class ProductSupplier(Base):
    __tablename__ = "product_suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "products.id",
            name="fk_product_suppliers_product_id_products",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "suppliers.id",
            name="fk_product_suppliers_supplier_id_suppliers",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_product_suppliers_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    purchase_price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    margin_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    sale_price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    product: Mapped["Product"] = relationship(
        back_populates="supplier_links",
    )
    supplier: Mapped["Supplier"] = relationship(
        back_populates="product_links",
    )
    restock_lines: Mapped[list["RestockLine"]] = relationship(
        back_populates="product_supplier",
    )
    sale_lines: Mapped[list["SaleLine"]] = relationship(
        back_populates="product_supplier",
    )

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "supplier_id",
            "workspace_id",
            name="uq_product_suppliers_product_supplier_workspace",
        ),
        CheckConstraint(
            "purchase_price > 0",
            name="ck_product_suppliers_purchase_price",
        ),
        CheckConstraint(
            "margin_percent >= 0",
            name="ck_product_suppliers_margin_percent",
        ),
        CheckConstraint("sale_price > 0", name="ck_product_suppliers_sale_price"),
        CheckConstraint(
            "sale_price * 100 >= purchase_price * (100 + margin_percent)",
            name="ck_product_suppliers_sale_price_floor",
        ),
        CheckConstraint("quantity >= 0", name="ck_product_suppliers_quantity"),
    )

    @property
    def floor_price(self) -> int:
        return calculate_floor_price(self.purchase_price, self.margin_percent)

    @property
    def stock_status(self) -> str:
        if self.quantity == 0:
            return "out"
        if 0 < self.quantity <= self.product.low_stock_threshold:
            return "low"
        return "available"

    @property
    def supplier_name(self) -> str | None:
        return self.supplier.name if self.supplier else None

    @property
    def product_name(self) -> str | None:
        return self.product.name if self.product else None


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_companies_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    iin: Mapped[str | None] = mapped_column(
        String(12),
        default=None,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="company",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "iin", name="uq_companies_workspace_iin"),
        UniqueConstraint("workspace_id", "name", name="uq_companies_workspace_name"),
    )


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_suppliers_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
    )

    product_links: Mapped[list["ProductSupplier"]] = relationship(
        back_populates="supplier",
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_suppliers_workspace_name",
        ),
        UniqueConstraint(
            "workspace_id",
            "phone_number",
            name="uq_suppliers_workspace_phone_number",
        ),
        CheckConstraint(
            "phone_number ~ '^(8[0-9]{10}|\\+7[0-9]{10})$'",
            name="ck_suppliers_phone_number",
        ),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_tags_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    products: Mapped[list["Product"]] = relationship(
        secondary=product_tags,
        back_populates="tags",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_tags_workspace_name"),
        CheckConstraint("char_length(name) > 0", name="ck_tags_name_not_empty"),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "companies.id",
            name="fk_products_company_id_companies",
        ),
        nullable=False,
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_products_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    quantity_unit: Mapped[str] = mapped_column(
        String(QUANTITY_UNIT_MAX_LENGTH),
        default=DEFAULT_QUANTITY_UNIT,
        server_default=DEFAULT_QUANTITY_UNIT,
        nullable=False,
    )
    low_stock_threshold: Mapped[int] = mapped_column(
        Integer,
        default=5,
        server_default="5",
        nullable=False,
    )

    supplier_links: Mapped[list["ProductSupplier"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductSupplier.id",
    )
    company: Mapped["Company"] = relationship(back_populates="products")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=product_tags,
        back_populates="products",
        order_by="Tag.name",
    )

    @property
    def company_name(self) -> str | None:
        return self.company.name if self.company else None

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            "company_id",
            "quantity_unit",
            name="uq_products_workspace_name_company_unit",
        ),
        CheckConstraint(
            "char_length(quantity_unit) > 0",
            name="ck_products_quantity_unit_not_empty",
        ),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_products_low_stock_threshold",
        ),
    )


class Restock(Base):
    __tablename__ = "restocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_restocks_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    lines: Mapped[list["RestockLine"]] = relationship(
        back_populates="restock",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RestockLine.id",
    )


class RestockLine(Base):
    __tablename__ = "restock_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_restock_lines_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    restock_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "restocks.id",
            name="fk_restock_lines_restock_id_restocks",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    product_supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "product_suppliers.id",
            name="fk_restock_lines_product_supplier_id_product_suppliers",
        ),
        nullable=False,
    )

    restock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_cost_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    quantity_unit_snapshot: Mapped[str] = mapped_column(
        String(QUANTITY_UNIT_MAX_LENGTH),
        nullable=False,
    )

    restock: Mapped["Restock"] = relationship(
        back_populates="lines",
    )
    product_supplier: Mapped["ProductSupplier"] = relationship(
        back_populates="restock_lines",
    )

    __table_args__ = (
        CheckConstraint(
            "restock_quantity > 0",
            name="ck_restock_lines_restock_quantity",
        ),
        UniqueConstraint(
            "workspace_id",
            "restock_id",
            "product_supplier_id",
            name="uq_restock_lines_workspace_restock_product_supplier",
        ),
    )

    @property
    def product_id(self) -> int:
        return self.product_supplier.product_id

    @property
    def product_name(self) -> str | None:
        return self.product_supplier.product_name

    @property
    def supplier_id(self) -> int:
        return self.product_supplier.supplier_id

    @property
    def supplier_name(self) -> str | None:
        return self.product_supplier.supplier_name


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_sales_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    lines: Mapped[list["SaleLine"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SaleLine.id",
    )


class SaleLine(Base):
    __tablename__ = "sale_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_sale_lines_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    sale_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "sales.id",
            name="fk_sale_lines_sale_id_sales",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    product_supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "product_suppliers.id",
            name="fk_sale_lines_product_supplier_id_product_suppliers",
        ),
        nullable=False,
    )

    sale_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_cost_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_sale_price_snapshot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    quantity_unit_snapshot: Mapped[str] = mapped_column(
        String(QUANTITY_UNIT_MAX_LENGTH),
        nullable=False,
    )

    sale: Mapped["Sale"] = relationship(
        back_populates="lines",
    )
    product_supplier: Mapped["ProductSupplier"] = relationship(
        back_populates="sale_lines",
    )

    __table_args__ = (
        CheckConstraint(
            "sale_quantity > 0",
            name="ck_sale_lines_sale_quantity",
        ),
        UniqueConstraint(
            "workspace_id",
            "sale_id",
            "product_supplier_id",
            name="uq_sale_lines_workspace_sale_product_supplier",
        ),
    )

    @property
    def product_id(self) -> int:
        return self.product_supplier.product_id

    @property
    def product_name(self) -> str | None:
        return self.product_supplier.product_name

    @property
    def supplier_id(self) -> int:
        return self.product_supplier.supplier_id

    @property
    def supplier_name(self) -> str | None:
        return self.product_supplier.supplier_name


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    workspace_memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(email) > 0",
            name="ck_users_email_not_empty",
        ),
        CheckConstraint(
            "char_length(password_hash) > 0",
            name="ck_users_password_not_empty",
        ),
        CheckConstraint(
            "char_length(name) > 0",
            name="ck_users_name_not_empty",
        ),
        UniqueConstraint(
            "email",
            name="uq_users_email",
        ),
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(name) > 0",
            name="ck_workspaces_name_not_empty",
        ),
        UniqueConstraint(
            "name",
            name="uq_workspaces_name",
        ),
    )


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "users.id",
            name="fk_workspace_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_workspace_memberships_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="memberships",
    )
    user: Mapped["User"] = relationship(
        back_populates="workspace_memberships",
    )

    __table_args__ = (
        CheckConstraint(
            "role in ('owner', 'admin', 'manager', 'operator', 'viewer')",
            name="ck_workspace_membership_role",
        ),
        UniqueConstraint(
            "user_id",
            "workspace_id",
            name="uq_workspace_memberships_user_workspace",
        ),
    )


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "workspaces.id",
            name="fk_workspace_invitations_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    inviter_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "users.id",
            name="fk_workspace_invitations_inviter_user_id_users",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_workspace_invitations_token_hash",
        ),
        CheckConstraint(
            "role in ('admin', 'manager', 'operator', 'viewer')",
            name="ck_workspace_invitations_role",
        ),
        CheckConstraint(
            "char_length(email) > 0",
            name="ck_workspace_invitations_email_not_empty",
        ),
        CheckConstraint(
            "char_length(token_hash) > 0",
            name="ck_workspace_invitations_token_hash_not_empty",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_workspace_invitations_expires_after_created",
        ),
        CheckConstraint(
            "accepted_at is null or revoked_at is null",
            name="ck_workspace_invitations_not_accepted_and_revoked",
        ),
    )
