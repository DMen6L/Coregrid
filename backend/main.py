from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
