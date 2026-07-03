from fastapi import FastAPI

from routers import companies, products, suppliers

app = FastAPI()

app.include_router(companies.router)
app.include_router(suppliers.router)
app.include_router(products.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}
