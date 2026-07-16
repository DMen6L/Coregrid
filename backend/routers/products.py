from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.models import Product
from app.schemas import ProductResponse
from devs import DbSession


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse], status_code=200)
def get_product_by_name(db: DbSession, search: str | None = None):
    statement = select(Product)

    if search and (search := search.strip()):
        statement = statement.where(Product.name.ilike(f"%{search}%"))

    return db.scalars(statement).all()
