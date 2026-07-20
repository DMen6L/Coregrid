from datetime import datetime

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

from app.db import Base
from app.pricing import calculate_floor_price
from app.units import DEFAULT_QUANTITY_UNIT, QUANTITY_UNIT_MAX_LENGTH


# ======
# MODELS
# ======

product_tags = Table(
    "product_tags",
    Base.metadata,
    Column(
        "product_id",
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    iin: Mapped[str] = mapped_column(
        String(12),
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
        UniqueConstraint("iin", name="uq_companies_iin"),
        UniqueConstraint("name", name="uq_companies_name"),
    )


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="supplier",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_suppliers_name"),
        UniqueConstraint("phone_number", name="uq_suppliers_phone_number"),
        CheckConstraint(
            "phone_number ~ '^(8[0-9]{10}|\\+7[0-9]{10})$'",
            name="ck_suppliers_phone_number",
        ),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
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
        UniqueConstraint("name", name="uq_tags_name"),
        CheckConstraint("char_length(name) > 0", name="ck_tags_name_not_empty"),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    supplier_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
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
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    company: Mapped["Company | None"] = relationship(back_populates="products")
    supplier: Mapped["Supplier | None"] = relationship(back_populates="products")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=product_tags,
        back_populates="products",
        order_by="Tag.name",
    )
    restock_lines: Mapped[list["RestockLine"]] = relationship(
        back_populates="product",
    )
    sale_lines: Mapped[list["SaleLine"]] = relationship(
        back_populates="product",
    )

    __table_args__ = (
        CheckConstraint("purchase_price > 0", name="ck_products_purchase_price"),
        CheckConstraint("margin_percent >= 0", name="ck_products_margin_percent"),
        CheckConstraint("sale_price > 0", name="ck_products_sale_price"),
        CheckConstraint(
            "sale_price * 100 >= purchase_price * (100 + margin_percent)",
            name="ck_products_sale_price_floor",
        ),
        CheckConstraint("quantity >= 0", name="ck_products_quantity"),
        CheckConstraint(
            "char_length(quantity_unit) > 0",
            name="ck_products_quantity_unit_not_empty",
        ),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_products_low_stock_threshold",
        ),
    )

    @property
    def floor_price(self) -> int:
        return calculate_floor_price(self.purchase_price, self.margin_percent)

    @property
    def stock_status(self) -> str:
        if self.quantity == 0:
            return "out"
        if 0 < self.quantity <= self.low_stock_threshold:
            return "low"
        return "available"

    @property
    def company_name(self) -> str | None:
        return self.company.name if self.company else None

    @property
    def supplier_name(self) -> str | None:
        return self.supplier.name if self.supplier else None


class Restock(Base):
    __tablename__ = "restocks"

    id: Mapped[int] = mapped_column(primary_key=True)
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
    restock_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("restocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    restock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_cost_snapshot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    quantity_unit_snapshot: Mapped[str] = mapped_column(
        String(QUANTITY_UNIT_MAX_LENGTH),
        nullable=False,
    )

    restock: Mapped["Restock"] = relationship(
        back_populates="lines",
    )
    product: Mapped["Product"] = relationship(
        back_populates="restock_lines",
    )

    __table_args__ = (
        CheckConstraint(
            "restock_quantity > 0",
            name="ck_restock_lines_requested_restock",
        ),
        UniqueConstraint(
            "restock_id",
            "product_id",
            name="uq_restock_lines_restock_product",
        ),
    )


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)

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
    sale_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    sale_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_cost_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )
    unit_sale_price_snapshot: Mapped[int] = mapped_column(
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
    product: Mapped["Product"] = relationship(
        back_populates="sale_lines",
    )

    __table_args__ = (
        CheckConstraint(
            "sale_quantity > 0",
            name="ck_sale_lines_sale_quantity",
        ),
        UniqueConstraint(
            "sale_id",
            "product_id",
            name="uq_sale_lines_sale_product",
        ),
    )
