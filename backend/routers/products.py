from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import selectinload

from app.models import Company, Product, Supplier, Tag
from app.pricing import calculate_floor_price
from app.schemas import (
    PaginatedResponse,
    ProductCreate,
    ProductResponse,
    ProductSummaryResponse,
    ProductUpdate,
    TagName,
)
from app.tags import get_or_create_tags, normalize_tag_name, normalize_tag_names
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(prefix="/products", tags=["products"])
ProductStockFilter = Literal["all", "available", "low", "empty"]
ProductSort = Literal[
    "name",
    "quantity",
    "stock_status",
    "inventory_value",
    "company",
    "supplier",
    "created_at",
]
SortOrder = Literal["asc", "desc"]
SALE_PRICE_FLOOR_ERROR = "sale_price cannot be lower than floor_price"
TAGS_NULL_ERROR = "tags cannot be null"
QUANTITY_UNIT_NULL_ERROR = "quantity_unit cannot be null"


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
        quantity_unit=product_data.quantity_unit,
        low_stock_threshold=product_data.low_stock_threshold,
        company_id=product_data.company_id,
        supplier_id=product_data.supplier_id,
    )
    new_product.tags = get_or_create_tags(db, product_data.tags)

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
    tag_names = None

    if "tags" in changes:
        tag_names = changes.pop("tags")
        if tag_names is None:
            raise HTTPException(status_code=422, detail=TAGS_NULL_ERROR)

    if "quantity_unit" in changes and changes["quantity_unit"] is None:
        raise HTTPException(status_code=422, detail=QUANTITY_UNIT_NULL_ERROR)

    validate_product_pricing_update(product, changes)

    for field, value in changes.items():
        setattr(product, field, value)

    if tag_names is not None:
        product.tags = get_or_create_tags(db, tag_names)

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
    tag: Annotated[str | None, Query(max_length=50)] = None,
    tags: Annotated[list[TagName] | None, Query()] = None,
    sort: ProductSort = "created_at",
    order: SortOrder = "asc",
) -> dict[str, object]:
    query = db.query(Product).options(
        selectinload(Product.company),
        selectinload(Product.supplier),
        selectinload(Product.tags),
    )

    search_term = search.strip() if search else ""
    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.company.has(Company.name.ilike(pattern)),
                Product.supplier.has(Supplier.name.ilike(pattern)),
                Product.tags.any(Tag.name.ilike(pattern)),
            )
        )

    tag_terms = normalize_tag_names(tags or [])
    legacy_tag_term = normalize_tag_name(tag) if tag else ""
    if legacy_tag_term:
        tag_terms = normalize_tag_names([*tag_terms, legacy_tag_term])

    for tag_term in tag_terms:
        tag_conditions = [Product.tags.any(Tag.name == tag_term)]
        if tag_term.isdecimal():
            tag_conditions.append(Product.tags.any(Tag.id == int(tag_term)))
        query = query.filter(or_(*tag_conditions))

    if stock == "available":
        query = query.filter(Product.quantity > 0)
    elif stock == "low":
        query = query.filter(
            Product.quantity > 0,
            Product.quantity <= Product.low_stock_threshold,
        )
    elif stock == "empty":
        query = query.filter(Product.quantity == 0)

    return paginate(apply_product_sorting(query, sort, order), page, page_size)


def apply_product_sorting(query, sort: ProductSort, order: SortOrder):
    is_desc = order == "desc"

    if sort == "company":
        sort_expression = Company.name.desc() if is_desc else Company.name.asc()
        return query.outerjoin(Product.company).order_by(
            Company.name.is_(None),
            sort_expression,
            Product.id,
        )

    if sort == "supplier":
        sort_expression = Supplier.name.desc() if is_desc else Supplier.name.asc()
        return query.outerjoin(Product.supplier).order_by(
            Supplier.name.is_(None),
            sort_expression,
            Product.id,
        )

    if sort == "stock_status":
        status_sort = case(
            (Product.quantity == 0, 0),
            (
                and_(
                    Product.quantity > 0,
                    Product.quantity <= Product.low_stock_threshold,
                ),
                1,
            ),
            else_=2,
        )
        sort_expression = status_sort.desc() if is_desc else status_sort.asc()
        return query.order_by(sort_expression, Product.id)

    sort_expressions = {
        "name": Product.name,
        "quantity": Product.quantity,
        "inventory_value": Product.purchase_price * Product.quantity,
        "created_at": Product.created_at,
    }
    sort_expression = sort_expressions[sort]
    sort_expression = sort_expression.desc() if is_desc else sort_expression.asc()

    return query.order_by(sort_expression, Product.id)


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
    total_products, total_units, inventory_value, low_stock, out_of_stock = db.query(
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
        func.coalesce(
            func.sum(
                case(
                    (Product.quantity == 0, 1),
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
        out_of_stock=int(out_of_stock),
    )


@router.get("/{id}", response_model=ProductResponse, status_code=200)
def get_product(id: int, db: DbSession) -> Product:
    product = (
        db.query(Product)
        .options(
            selectinload(Product.company),
            selectinload(Product.supplier),
            selectinload(Product.tags),
        )
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
