from fastapi import status
import pytest
from sqlalchemy import text

from app.db import SessionLocal, engine


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
def second_user_data():
    return {
        "name": "Second User",
        "email": "second@email.com",
        "password": "AnotherStrong102",
    }


@pytest.fixture
def registered_second_user(client, second_user_data):
    response = client.post("/auth/register", json=second_user_data)

    assert response.status_code == status.HTTP_201_CREATED
    return second_user_data


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
def second_auth_headers(client, registered_second_user) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={
            "email": registered_second_user["email"],
            "password": registered_second_user["password"],
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


@pytest.fixture
def supplier(
    client,
    auth_headers,
    workspace,
):
    payload = {
        "name": "new_supplier",
        "phone_number": "+77070707070",
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/suppliers",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def product(
    client,
    auth_headers,
    workspace,
    company,
):
    payload = {
        "name": "new_product",
        "company_id": company["id"],
        "tags": ["test tag", "second tag"],
        "quantity_unit": "шт",
        "low_stock_threshold": 5,
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/products",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def product_with_link(
    client,
    auth_headers,
    workspace,
    company,
    supplier,
):
    payload = {
        "product_name": "linked_product",
        "company_id": company["id"],
        "tags": ["linked tag"],
        "quantity_unit": "шт",
        "low_stock_threshold": 5,
        "product_links": [
            {
                "supplier_id": supplier["id"],
                "purchase_price": 100,
                "margin_percent": 20,
                "sale_price": 130,
                "quantity": 7,
            }
        ],
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/products/full",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def product_supplier_link(product_with_link):
    assert len(product_with_link["supplier_links"]) == 1
    return product_with_link["supplier_links"][0]


@pytest.fixture
def empty_product_with_link(
    client,
    auth_headers,
    workspace,
    company,
    supplier,
):
    payload = {
        "product_name": "empty_link_product",
        "company_id": company["id"],
        "tags": ["delete tag"],
        "quantity_unit": "шт",
        "low_stock_threshold": 5,
        "product_links": [
            {
                "supplier_id": supplier["id"],
                "purchase_price": 100,
                "margin_percent": 20,
                "sale_price": 130,
                "quantity": 0,
            }
        ],
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/products/full",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def empty_product_supplier_link(empty_product_with_link):
    assert len(empty_product_with_link["supplier_links"]) == 1
    return empty_product_with_link["supplier_links"][0]


@pytest.fixture
def invitation(
    client,
    auth_headers,
    workspace,
    registered_second_user,
):
    payload = {
        "email": registered_second_user["email"],
        "role": "viewer",
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def accepted_member(
    client,
    auth_headers,
    second_auth_headers,
    workspace,
    invitation,
    registered_second_user,
):
    response = client.post(
        f"/me/accept/{invitation['id']}",
        headers=second_auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.get(
        f"/workspaces/{workspace['id']}/members",
        params={"search": registered_second_user["email"]},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data["items"]) == 1
    return data["items"][0]


@pytest.fixture
def owner_member(
    client,
    auth_headers,
    workspace,
    registered_user,
):
    response = client.get(
        f"/workspaces/{workspace['id']}/members",
        params={"search": registered_user["email"]},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data["items"]) == 1
    return data["items"][0]


@pytest.fixture
def restock(
    client,
    auth_headers,
    workspace,
    product_supplier_link,
):
    payload = {
        "note": "test restock",
        "lines": [
            {
                "product_supplier_id": product_supplier_link["id"],
                "restock_quantity": 3,
                "unit_cost_snapshot": 90,
            }
        ],
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/restocks",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def sale(
    client,
    auth_headers,
    workspace,
    product_supplier_link,
):
    payload = {
        "note": "test sale",
        "lines": [
            {
                "product_supplier_id": product_supplier_link["id"],
                "sale_quantity": 2,
            }
        ],
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/sales",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()
