from datetime import date, datetime, time, timedelta

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, select

from app.schemas import SummariesResponse
from app.models import Product, StockMovement, StockMovementLine

from devs import DbSession
from routers import companies, products, sales, stock_movements, suppliers, tags


LOCAL_DEVELOPMENT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_DEVELOPMENT_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(stock_movements.router)
app.include_router(tags.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/summaries", response_model=SummariesResponse, status_code=status.HTTP_200_OK)
def get_summaries(db: DbSession) -> SummariesResponse:
    today = date.today()
    start_of_today = datetime.combine(today, time.min)
    start_of_tomorrow = start_of_today + timedelta(days=1)

    sales_value_subquery = (
        select(
            func.coalesce(
                func.sum(
                    StockMovementLine.quantity_delta
                    * StockMovementLine.unit_price_snapshot
                ),
                0,
            )
        )
        .select_from(StockMovementLine)
        .join(StockMovementLine.movement)
        .where(
            StockMovement.created_at >= start_of_today,
            StockMovement.created_at < start_of_tomorrow,
            StockMovement.movement_type == "out",
        )
        .scalar_subquery()
    )

    sales_count_subquery = (
        select(func.count(func.distinct(StockMovement.id)))
        .where(
            StockMovement.created_at >= start_of_today,
            StockMovement.created_at < start_of_tomorrow,
            StockMovement.movement_type == "out",
        )
        .scalar_subquery()
    )

    low_stock_subquery = (
        select(func.count(func.distinct(Product.id)))
        .where(Product.quantity > 0, Product.quantity <= Product.low_stock_threshold)
        .scalar_subquery()
    )

    out_of_stock_subquery = (
        select(func.count(func.distinct(Product.id)))
        .where(Product.quantity == 0)
        .scalar_subquery()
    )

    statement = select(
        sales_value_subquery.label("dashboard_sales_value"),
        sales_count_subquery.label("dashboard_sales_count"),
        low_stock_subquery.label("low_stock"),
        out_of_stock_subquery.label("out_of_stock"),
    )

    result = db.execute(statement).one()

    return SummariesResponse(
        dashboard_sales_value=result.dashboard_sales_value,
        dashboard_sales_count=result.dashboard_sales_count,
        low_stock=result.low_stock,
        out_of_stock=result.out_of_stock,
    )
