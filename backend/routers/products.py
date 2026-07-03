from fastapi import APIRouter, HTTPException

from app.models import Product
from app.schemas import ProductCreate, ProductResponse, ProductUpdate
from devs import DbSession
from errors import commit_or_raise


router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=201)
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


@router.patch("/{id}", response_model=ProductResponse, status_code=200)
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


@router.get("", response_model=list[ProductResponse], status_code=200)
def get_products(db: DbSession) -> list[Product]:
    return db.query(Product).all()


@router.get("/{id}", response_model=ProductResponse, status_code=200)
def get_product(id: int, db: DbSession) -> Product:
    product = db.get(Product, id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.delete("/{id}", status_code=204)
def delete_product(id: int, db: DbSession) -> None:
    product = db.get(Product, id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    commit_or_raise(db)
