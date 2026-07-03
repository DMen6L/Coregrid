from fastapi import APIRouter, HTTPException

from app.models import Supplier
from app.schemas import SupplierCreate, SupplierResponse, SupplierUpdate
from devs import DbSession
from errors import commit_or_raise


router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierResponse, status_code=201)
def add_supplier(supplier_data: SupplierCreate, db: DbSession) -> Supplier:
    new_supplier = Supplier(
        name=supplier_data.name, phone_number=supplier_data.phone_number
    )

    db.add(new_supplier)
    commit_or_raise(db)
    db.refresh(new_supplier)

    return new_supplier


@router.patch("/{id}", response_model=SupplierResponse, status_code=200)
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


@router.get("", response_model=list[SupplierResponse], status_code=200)
def get_suppliers(db: DbSession) -> list[Supplier]:
    return db.query(Supplier).all()


@router.get("/{id}", response_model=SupplierResponse, status_code=200)
def get_supplier(id: int, db: DbSession) -> Supplier:
    supplier = db.get(Supplier, id)

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return supplier


@router.delete("/{id}", status_code=204)
def delete_supplier(id: int, db: DbSession) -> None:
    supplier = db.get(Supplier, id)

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db.delete(supplier)
    commit_or_raise(db)
