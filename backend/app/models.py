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

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    company: Mapped["Company"] = relationship(back_populates="products")
    supplier: Mapped["Supplier"] = relationship(back_populates="products")

    __table_args__ = (
        CheckConstraint("price > 0", name="ck_products_price"),
        CheckConstraint("quantity >= 0", name="ck_products_quantity"),
    )
