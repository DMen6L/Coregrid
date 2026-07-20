from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, select

from app.schemas import DailySalesResponse, SummariesResponse
from app.models import Product, Sale, SaleLine

from devs import DbSession
from routers import companies, products, restocks, sales, suppliers, tags


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
app.include_router(restocks.router)
app.include_router(sales.router)
app.include_router(tags.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/summaries", response_model=SummariesResponse, status_code=status.HTTP_200_OK)
def get_summaries(
    db: DbSession, days_ago: Annotated[int, Query(ge=7, le=365)] = 7
) -> SummariesResponse:
    today = date.today()
    start_of_today = datetime.combine(today, time.min)
    start_of_tomorrow = start_of_today + timedelta(days=1)
    start_of_period = start_of_today - timedelta(days=days_ago - 1)

    dashboard_sales_value_subquery = (
        select(
            func.coalesce(
                func.sum(SaleLine.unit_sale_price_snapshot * SaleLine.sale_quantity),
                0,
            )
        )
        .join(SaleLine.sale)
        .where(Sale.created_at >= start_of_today, Sale.created_at < start_of_tomorrow)
        .scalar_subquery()
    )
    dashboard_sales_count_subquery = (
        select(func.count(func.distinct(Sale.id)))
        .where(Sale.created_at >= start_of_today, Sale.created_at < start_of_tomorrow)
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
        dashboard_sales_value_subquery.label("dashboard_sales_value"),
        dashboard_sales_count_subquery.label("dashboard_sales_count"),
        low_stock_subquery.label("low_stock"),
        out_of_stock_subquery.label("out_of_stock"),
    )

    sale_date = func.date(Sale.created_at)
    latest_sales_statement = (
        select(
            sale_date.label("date"),
            func.coalesce(
                func.sum(SaleLine.unit_sale_price_snapshot * SaleLine.sale_quantity),
                0,
            ).label("sales_value"),
        )
        .select_from(SaleLine)
        .join(SaleLine.sale)
        .where(
            Sale.created_at >= start_of_period,
            Sale.created_at < start_of_tomorrow,
        )
        .group_by(sale_date)
        .order_by(sale_date)
    )

    result = db.execute(statement).one()
    latest_sales = db.execute(latest_sales_statement).all()
    sales_by_day = [
        DailySalesResponse(
            date=latest_sale.date,
            sales_value=latest_sale.sales_value,
        )
        for latest_sale in latest_sales
    ]

    return SummariesResponse(
        dashboard_sales_value=result.dashboard_sales_value,
        dashboard_sales_count=result.dashboard_sales_count,
        low_stock=result.low_stock,
        out_of_stock=result.out_of_stock,
        latest_sales=sales_by_day,
    )
