from collections.abc import Generator
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException

from sqlalchemy.orm import Session

from psycopg.errors import UniqueViolation, ForeignKeyViolation, CheckViolation
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal, engine, Base
from app.models import Company, Supplier, Product
from app.schemas import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]


def commit_or_raise(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        if isinstance(exc.orig, UniqueViolation):
            raise HTTPException(
                status_code=409, detail="Duplicate value conflicts existing row"
            ) from exc
        if isinstance(exc.orig, ForeignKeyViolation):
            raise HTTPException(
                status_code=409, detail="Referenced row does not exist or was changed"
            ) from exc
        if isinstance(exc.orig, CheckViolation):
            raise HTTPException(
                status_code=422, detail="Value violates a database constraint"
            ) from exc

        raise HTTPException(status_code=500, detail="Database error") from exc


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


# =========================
# ADDITION OF NEW INSTANCES
# =========================


@app.post("/companies", response_model=CompanyResponse, status_code=201)
def add_company(company_data: CompanyCreate, db: DbSession) -> Company:
    new_company = Company(iin=company_data.iin, name=company_data.name)

    db.add(new_company)
    commit_or_raise(db)
    db.refresh(new_company)

    return new_company


@app.post("/suppliers", response_model=SupplierResponse, status_code=201)
def add_supplier(supplier_data: SupplierCreate, db: DbSession) -> Supplier:
    new_supplier = Supplier(
        name=supplier_data.name, phone_number=supplier_data.phone_number
    )

    db.add(new_supplier)
    commit_or_raise(db)
    db.refresh(new_supplier)

    return new_supplier


@app.post("/products", response_model=ProductResponse, status_code=201)
def add_product(product_data: ProductCreate, db: DbSession) -> Product:
    new_product = Product(
        name=product_data.name,
        price=product_data.price,
        quantity=product_data.quantity,
        company_id=product_data.company_id,
        supplier_id=product_data.supplier_id,
    )

    db.add(new_product)
    commit_or_raise(db)
    db.refresh(new_product)

    return new_product


# ===============
# UPDATING TABLES
# ===============


@app.patch("/companies/{id}", response_model=CompanyResponse, status_code=200)
def patch_company(id: int, update_data: CompanyUpdate, db: DbSession) -> Company:
    company = db.get(Company, id)

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    changes = update_data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(company, field, value)

    commit_or_raise(db)
    db.refresh(company)

    return company


@app.patch("/suppliers/{id}", response_model=SupplierResponse, status_code=200)
def patch_supplier(id: int, update_data: SupplierUpdate, db: DbSession) -> Supplier:
    supplier = db.get(Supplier, id)

    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    changes = update_data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(supplier, field, value)

    commit_or_raise(db)
    db.refresh(supplier)

    return supplier


@app.patch("/products/{id}", response_model=ProductResponse, status_code=200)
def patch_product(id: int, update_data: ProductUpdate, db: DbSession) -> Product:
    product = db.get(Product, id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    changes = update_data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(product, field, value)

    commit_or_raise(db)
    db.refresh(product)

    return product


# =======================
# SELECTING ALL INSTANCES
# =======================


@app.get("/companies", response_model=list[CompanyResponse], status_code=200)
def get_companies(db: DbSession) -> list[Company]:
    return db.query(Company).all()


@app.get("/suppliers", response_model=list[SupplierResponse], status_code=200)
def get_suppliers(db: DbSession) -> list[Supplier]:
    return db.query(Supplier).all()


@app.get("/products", response_model=list[ProductResponse], status_code=200)
def get_products(db: DbSession) -> list[Product]:
    return db.query(Product).all()


# ==========================
# SELECTING SINGLE INSTANCES
# ==========================


@app.get("/companies/{id}", response_model=CompanyResponse, status_code=200)
def get_company(id: int, db: DbSession) -> Company:
    company = db.get(Company, id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


@app.get("/suppliers/{id}", response_model=SupplierResponse, status_code=200)
def get_supplier(id: int, db: DbSession) -> Supplier:
    supplier = db.get(Supplier, id)

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return supplier


@app.get("/products/{id}", response_model=ProductResponse, status_code=200)
def get_product(id: int, db: DbSession) -> Product:
    product = db.get(Product, id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


# ==================
# DELETING INSTANCES
# ==================


@app.delete("/products/{id}", status_code=204)
def delete_company(id: int, db: DbSession) -> None:
    company = db.get(Product, id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(company)
    commit_or_raise(db)


@app.delete("/products/{id}", status_code=204)
def delete_supplier(id: int, db: DbSession) -> None:
    supplier = db.get(Product, id)

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db.delete(supplier)
    commit_or_raise(db)


@app.delete("/products/{id}", status_code=204)
def delete_product(id: int, db: DbSession) -> None:
    product = db.get(Product, id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    commit_or_raise(db)
