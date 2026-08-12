import pytest
from sqlalchemy import text

from app.db import SessionLocal, engine


TABLES_TO_TRUNCATE = (
    "sale_lines",
    "sales",
    "restock_lines",
    "restocks",
    "product_tags",
    "product_suppliers",
    "products",
    "tags",
    "suppliers",
    "companies",
    "workspace_invitations",
    "workspace_memberships",
    "workspaces",
    "users",
)


def truncate_test_data() -> None:
    table_names = ", ".join(TABLES_TO_TRUNCATE)

    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )


@pytest.fixture(autouse=True)
def clean_database():
    truncate_test_data()
    yield
    truncate_test_data()


@pytest.fixture
def db_session():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as test_client:
        yield test_client
