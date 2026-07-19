from datetime import date, datetime, time, timedelta

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, select

from app.schemas import SummariesResponse
from app.models import Product

from devs import DbSession
from routers import companies, products, restocks, suppliers, tags


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
app.include_router(tags.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/summaries", response_model=SummariesResponse, status_code=status.HTTP_200_OK)
def get_summaries(db: DbSession) -> SummariesResponse:
    today = date.today()
    start_of_today = datetime.combine(today, time.min)
    start_of_tomorrow = start_of_today + timedelta(days=1)

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
        low_stock_subquery.label("low_stock"),
        out_of_stock_subquery.label("out_of_stock"),
    )

    result = db.execute(statement).one()

    return SummariesResponse(
        dashboard_sales_value=0,
        dashboard_sales_count=0,
        low_stock=result.low_stock,
        out_of_stock=result.out_of_stock,
    )
