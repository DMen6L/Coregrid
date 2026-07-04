from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import selectinload

from app.models import Company, Product, Supplier
from app.pricing import calculate_floor_price
from app.schemas import (
    PaginatedResponse,
    ProductCreate,
    ProductResponse,
    ProductSummaryResponse,
    ProductUpdate,
)
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/products", tags=["products"])
ProductStockFilter = Literal["all", "available", "low", "empty"]
SALE_PRICE_FLOOR_ERROR = "sale_price cannot be lower than floor_price"


@router.post("", response_model=ProductResponse, status_code=201)
def add_product(product_data: ProductCreate, db: DbSession) -> Product:
    floor_price = calculate_floor_price(
        product_data.purchase_price,
        product_data.margin_percent,
    )
    new_product = Product(
        name=product_data.name,
        purchase_price=product_data.purchase_price,
        margin_percent=product_data.margin_percent,
        sale_price=product_data.sale_price or floor_price,
        quantity=product_data.quantity,
        low_stock_threshold=product_data.low_stock_threshold,
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
    validate_product_pricing_update(product, changes)

    for field, value in changes.items():
        setattr(product, field, value)

    commit_or_raise(db)
    db.refresh(product)

    return product


@router.get("", response_model=PaginatedResponse[ProductResponse], status_code=200)
def get_products(
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = DEFAULT_PAGE_SIZE,
    search: Annotated[str | None, Query(max_length=255)] = None,
    stock: ProductStockFilter = "all",
) -> dict[str, object]:
    query = db.query(Product).options(
        selectinload(Product.company),
        selectinload(Product.supplier),
    )

    search_term = search.strip() if search else ""
    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.company.has(Company.name.ilike(pattern)),
                Product.supplier.has(Supplier.name.ilike(pattern)),
            )
        )

    if stock == "available":
        query = query.filter(Product.quantity > 0)
    elif stock == "low":
        query = query.filter(
            Product.quantity > 0,
            Product.quantity <= Product.low_stock_threshold,
        )
    elif stock == "empty":
        query = query.filter(Product.quantity == 0)

    return paginate(query.order_by(Product.id), page, page_size)


def validate_product_pricing_update(
    product: Product,
    changes: dict[str, object],
) -> None:
    for field in ("purchase_price", "margin_percent", "sale_price"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")

    purchase_price = int(changes.get("purchase_price", product.purchase_price))
    margin_percent = int(changes.get("margin_percent", product.margin_percent))
    sale_price = int(changes.get("sale_price", product.sale_price))
    floor_price = calculate_floor_price(purchase_price, margin_percent)

    if sale_price < floor_price:
        raise HTTPException(status_code=422, detail=SALE_PRICE_FLOOR_ERROR)


@router.get("/summary", response_model=ProductSummaryResponse, status_code=200)
def get_product_summary(db: DbSession) -> ProductSummaryResponse:
    total_products, total_units, inventory_value, low_stock = db.query(
        func.count(Product.id),
        func.coalesce(func.sum(Product.quantity), 0),
        func.coalesce(func.sum(Product.purchase_price * Product.quantity), 0),
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Product.quantity > 0,
                            Product.quantity <= Product.low_stock_threshold,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
    ).one()

    return ProductSummaryResponse(
        total_products=int(total_products),
        total_units=int(total_units),
        inventory_value=int(inventory_value),
        low_stock=int(low_stock),
    )


@router.get("/{id}", response_model=ProductResponse, status_code=200)
def get_product(id: int, db: DbSession) -> Product:
    product = (
        db.query(Product)
        .options(selectinload(Product.company), selectinload(Product.supplier))
        .filter(Product.id == id)
        .one_or_none()
    )

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
