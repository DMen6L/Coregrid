from typing import Annotated

from fastapi import FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import SummariesResponse
from app.type_definitions import BestSalesMode

from helpers.dependencies import DbSession
from helpers.services import build_summaries
from routers import (
    companies,
    products,
    restocks,
    sales,
    suppliers,
    tags,
    auth,
    workspaces,
)


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
app.include_router(auth.router)
app.include_router(workspaces.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}


@app.get(
    "/summaries",
    response_model=SummariesResponse,
    status_code=status.HTTP_200_OK,
)
def get_summaries(
    db: DbSession,
    days: Annotated[int, Query(ge=7, le=365)] = 7,
    best_sales_mode: Annotated[BestSalesMode, Query] = "quantity",
) -> SummariesResponse:
    return build_summaries(
        db=db,
        days=days,
        best_sales_mode=best_sales_mode,
    )
