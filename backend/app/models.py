from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ======
# MODELS
# ======


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
            "char_length(phone_number) = 12", name="ck_suppliers_phone_number"
        ),
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
    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
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

    company: Mapped["Company"] = relationship(back_populates="products")
    supplier: Mapped["Supplier"] = relationship(back_populates="products")
    stock_movement_lines: Mapped[list["StockMovementLine"]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("price > 0", name="ck_products_price"),
        CheckConstraint("quantity >= 0", name="ck_products_quantity"),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_products_low_stock_threshold",
        ),
    )

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


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    movement_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    lines: Mapped[list["StockMovementLine"]] = relationship(
        back_populates="movement",
        cascade="all, delete-orphan",
        order_by="StockMovementLine.id",
    )

    __table_args__ = (
        CheckConstraint(
            "movement_type in ('in', 'out', 'adjustment')",
            name="ck_stock_movements_type",
        ),
    )


class StockMovementLine(Base):
    __tablename__ = "stock_movement_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    movement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stock_movements.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
    )
    quantity_delta: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    quantity_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    quantity_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_price_snapshot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    movement: Mapped["StockMovement"] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship(back_populates="stock_movement_lines")

    __table_args__ = (
        CheckConstraint(
            "quantity_delta != 0",
            name="ck_stock_movement_lines_quantity_delta",
        ),
        CheckConstraint(
            "quantity_before >= 0",
            name="ck_stock_movement_lines_quantity_before",
        ),
        CheckConstraint(
            "quantity_after >= 0",
            name="ck_stock_movement_lines_quantity_after",
        ),
        CheckConstraint(
            "unit_price_snapshot is null or unit_price_snapshot > 0",
            name="ck_stock_movement_lines_unit_price_snapshot",
        ),
    )
