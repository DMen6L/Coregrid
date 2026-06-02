from os import name
from fastapi import FastAPI, Depends

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine, Base
from app.models import Company, Supplier, Product
from app.schemas import (
    CompanyCreate,
    CompanyResponse,
    SupplierCreate,
    SupplierResponse,
    ProductCreate,
    ProductResponse,
)


def get_db():
    with SessionLocal() as session:
        yield session


app = FastAPI()


@app.get("/")
def read_root():
    Base.metadata.create_all(bind=engine)
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


@app.patch("/companies/{id}", status_code=200)
def update_company(id: int):
    pass


# ===================
# CLEARING OUT TABLES
# ===================


@app.delete("/cleanup", status_code=204)
def cleanup(db: Session = Depends(get_db)):
    db.execute(
        text("TRUNCATE TABLE products, companies, suppliers RESTART IDENTITY CASCADE")
    )
    db.commit()
