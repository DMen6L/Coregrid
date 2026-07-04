from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload

from app.models import Product, StockMovement, StockMovementLine
from app.schemas import PaginatedResponse, StockMovementCreate, StockMovementResponse
from devs import DbSession
from errors import commit_or_raise
from pagination import DEFAULT_PAGE_SIZE, PageNumber, PageSize, paginate


router = APIRouter(tags=["stock movements"])


@router.post("/stock-movements", response_model=StockMovementResponse, status_code=201)
def add_stock_movement(
    movement_data: StockMovementCreate,
    db: DbSession,
) -> StockMovement:
    product_ids = [line.product_id for line in movement_data.lines]
    products = (
        db.query(Product)
        .filter(Product.id.in_(product_ids))
        .with_for_update()
        .all()
    )
    products_by_id = {product.id: product for product in products}

    for product_id in product_ids:
        if product_id not in products_by_id:
            raise HTTPException(status_code=404, detail="Product not found")

    new_movement = StockMovement(
        movement_type=movement_data.movement_type,
        note=movement_data.note,
    )
    db.add(new_movement)

    for line_data in movement_data.lines:
        product = products_by_id[line_data.product_id]
        quantity_before = product.quantity
        quantity_after = quantity_before + line_data.quantity_delta

        if quantity_after < 0:
            raise HTTPException(
                status_code=422,
                detail="Stock movement would make product quantity negative",
            )

        product.quantity = quantity_after
        new_movement.lines.append(
            StockMovementLine(
                product_id=product.id,
                quantity_delta=line_data.quantity_delta,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                unit_price_snapshot=product.price,
            )
        )

    commit_or_raise(db)
    db.refresh(new_movement)

    return new_movement


@router.get(
    "/stock-movements",
    response_model=PaginatedResponse[StockMovementResponse],
)
def get_stock_movements(
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = DEFAULT_PAGE_SIZE,
) -> dict[str, object]:
    query = (
        db.query(StockMovement)
        .options(selectinload(StockMovement.lines))
        .order_by(StockMovement.id)
    )

    return paginate(query, page, page_size)


@router.get("/stock-movements/{id}", response_model=StockMovementResponse)
def get_stock_movement(id: int, db: DbSession) -> StockMovement:
    movement = (
        db.query(StockMovement)
        .options(selectinload(StockMovement.lines))
        .filter(StockMovement.id == id)
        .one_or_none()
    )

    if movement is None:
        raise HTTPException(status_code=404, detail="Stock movement not found")

    return movement


@router.get(
    "/products/{product_id}/movements",
    response_model=PaginatedResponse[StockMovementResponse],
)
def get_product_stock_movements(
    product_id: int,
    db: DbSession,
    page: PageNumber = 1,
    page_size: PageSize = DEFAULT_PAGE_SIZE,
) -> dict[str, object]:
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    query = (
        db.query(StockMovement)
        .join(StockMovementLine)
        .options(selectinload(StockMovement.lines))
        .filter(StockMovementLine.product_id == product_id)
        .order_by(StockMovement.id)
    )

    return paginate(query, page, page_size)
