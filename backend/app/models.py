from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    iin: Mapped[str] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    products: Mapped[list["Product"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone_number: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)

    products: Mapped[list["Product"]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="products")
    supplier: Mapped["Supplier"] = relationship(back_populates="products")
