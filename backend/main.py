from os import name
from fastapi import FastAPI

from sqlalchemy import text

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

app = FastAPI()


@app.get("/")
def read_root():
    Base.metadata.create_all(bind=engine)
    return {"Hello": "World"}


# =========================
# ADDITION OF NEW INSTANCES
# =========================


@app.post("/add_company", status_code=201)
def add_company(company_data: CompanyCreate):
    with SessionLocal() as session:
        new_company = Company(iin=company_data.iin, name=company_data.name)

        session.add(new_company)
        session.commit()
        session.refresh(new_company)

        return {"Success": new_company}


@app.post("/add_supplier", status_code=201)
def add_supplier(supplier_data: SupplierCreate):
    with SessionLocal() as session:
        new_supplier = Supplier(
            name=supplier_data.name, phone_number=supplier_data.phone_number
        )

        session.add(new_supplier)
        session.commit()
        session.refresh(new_supplier)

        return {"Success": new_supplier}


@app.post("/add_product", status_code=201)
def add_product(product_data: ProductCreate):
    with SessionLocal() as session:
        new_product = Product(
            name=product_data.name,
            price=product_data.price,
            quantity=product_data.quantity,
            company_id=product_data.company_id,
            supplier_id=product_data.supplier_id,
        )

        session.add(new_product)
        session.commit()
        session.refresh(new_product)

        return {"Success": new_product}


# ===================
# CLEARING OUT TABLES
# ===================


@app.delete("/cleanup", status_code=204)
def cleanup():
    with SessionLocal() as session:
        _ = session.execute(
            text(
                "TRUNCATE TABLE products, companies, suppliers RESTART IDENTITY CASCADE"
            )
        )
        session.commit()
