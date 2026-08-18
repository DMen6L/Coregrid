from fastapi import status
import pytest
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.models import User, Workspace


TABLES_TO_TRUNCATE = (
    "audit_logs",
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


@pytest.fixture
def demo_user_data():
    return {
        "name": "Demo User",
        "email": "demo@email.com",
        "password": "StrongPassword102",
    }


@pytest.fixture
def registered_user(client, demo_user_data):
    response = client.post("/auth/register", json=demo_user_data)

    assert response.status_code == status.HTTP_201_CREATED
    return demo_user_data


@pytest.fixture
def auth_headers(client, registered_user) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == status.HTTP_200_OK

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def workspace(client, auth_headers):
    payload: dict[str, str] = {
        "name": "new_workspace",
    }
    response = client.post(
        "/workspaces",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def company(
    client,
    auth_headers,
    workspace,
):
    payload = {
        "name": "new_company",
        "iin": "070707070707",
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/companies",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()
