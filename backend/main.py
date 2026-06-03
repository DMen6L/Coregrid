from os import name
from fastapi import FastAPI, Depends, HTTPException

from sqlalchemy import text
from sqlalchemy.orm import Session

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


def get_db():
    with SessionLocal() as session:
        yield session


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


# =========================
# ADDITION OF NEW INSTANCES
# =========================


@app.post("/companies", response_model=CompanyResponse, status_code=201)
def add_company(company_data: CompanyCreate, db: Session = Depends(get_db)):
    new_company = Company(iin=company_data.iin, name=company_data.name)

    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return new_company


@app.post("/suppliers", response_model=SupplierResponse, status_code=201)
def add_supplier(supplier_data: SupplierCreate, db: Session = Depends(get_db)):
    new_supplier = Supplier(
        name=supplier_data.name, phone_number=supplier_data.phone_number
    )

    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)

    return new_supplier


@app.post("/products", response_model=ProductResponse, status_code=201)
def add_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    new_product = Product(
        name=product_data.name,
        price=product_data.price,
        quantity=product_data.quantity,
        company_id=product_data.company_id,
        supplier_id=product_data.supplier_id,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


# ===============
# UPDATING TABLES
# ===============


@app.patch("/companies/{id}", response_model=CompanyResponse, status_code=200)
def patch_company(id: int, update_data: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.get(Company, id)

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    changes = update_data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)

    return company


@app.patch("/suppliers/{id}", response_model=SupplierResponse, status_code=200)
def patch_supplier(id: int, update_data: SupplierUpdate, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, id)

    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    changes = update_data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)

    return supplier


@app.patch("/products/{id}", response_model=ProductResponse, status_code=200)
def patch_product(id: int, update_data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    changes = update_data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


# =======================
# SELECTING ALL INSTANCES
# =======================


@app.get("/companies", response_model=list[CompanyResponse], status_code=200)
def get_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()


@app.get("/suppliers", response_model=list[SupplierResponse], status_code=200)
def get_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()


@app.get("/products", response_model=list[ProductResponse], status_code=200)
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


# ==========================
# SELECTING SINGLE INSTANCES
# ==========================


@app.get("/companies/{id}", response_model=CompanyResponse, status_code=200)
def get_company(id: int, db: Session = Depends(get_db)):
    company = db.get(Company, id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


@app.get("/suppliers/{id}", response_model=SupplierResponse, status_code=200)
def get_supplier(id: int, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, id)

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return supplier


@app.get("/products/{id}", response_model=ProductResponse, status_code=200)
def get_product(id: int, db: Session = Depends(get_db)):
    product = db.get(Product, id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


# ===================
# CLEARING OUT TABLES
# ===================


@app.delete("/cleanup", status_code=204)
def cleanup(db: Session = Depends(get_db)):
    db.execute(
        text("TRUNCATE TABLE products, companies, suppliers RESTART IDENTITY CASCADE")
    )
    db.commit()
