from fastapi import FastAPI

from app.db import engine, Base
from app.models import Company, Supplier, Product

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}
