from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.models import Product
from app.schemas import ProductResponse
from devs import DbSession


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse], status_code=200)
def get_all_products(db: DbSession):
    return db.scalars(select(Product)).all()
