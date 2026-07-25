from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models import Company, ProductSupplier, Supplier
from main import app


client = TestClient(app)


def unique_suffix() -> str:
    return uuid4().hex[:10]


def unique_phone_number() -> str:
    return f"+7{uuid4().int % 10_000_000_000:010d}"


def create_company(db_session, suffix: str) -> Company:
    company = Company(
        name=f"Product test company {suffix}",
        iin=f"{uuid4().int % 1_000_000_000_000:012d}",
    )

    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    return company


def create_supplier(db_session, suffix: str) -> Supplier:
    supplier = Supplier(
        name=f"Product test supplier {suffix}",
        phone_number=unique_phone_number(),
    )

    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)

    return supplier


def create_product(payload: dict) -> dict:
    response = client.post("/products", json=payload)

    assert response.status_code == 201
    return response.json()


def assert_paginated_response(data: dict) -> None:
    assert set(data) == {
        "items",
        "page",
        "page_size",
        "total",
        "total_pages",
        "has_next",
        "has_previous",
    }
    assert isinstance(data["items"], list)
    assert isinstance(data["page"], int)
    assert isinstance(data["page_size"], int)
    assert isinstance(data["total"], int)
    assert isinstance(data["total_pages"], int)
    assert isinstance(data["has_next"], bool)
    assert isinstance(data["has_previous"], bool)


def assert_product_response_shape(product: dict) -> None:
    assert set(product) == {
        "id",
        "name",
        "created_at",
        "company_id",
        "company_name",
        "tags",
        "supplier_links",
    }
    assert isinstance(product["id"], int)
    assert isinstance(product["name"], str)
    assert datetime.fromisoformat(product["created_at"])
    assert product["company_id"] is None or isinstance(product["company_id"], int)
    assert product["company_name"] is None or isinstance(product["company_name"], str)
    assert isinstance(product["tags"], list)
    assert isinstance(product["supplier_links"], list)


def assert_product_supplier_response_shape(link: dict) -> None:
    assert set(link) == {
        "id",
        "product_id",
        "supplier_id",
        "product_name",
        "supplier_name",
        "purchase_price",
        "margin_percent",
        "floor_price",
        "sale_price",
        "quantity",
        "quantity_unit",
        "low_stock_threshold",
        "stock_status",
    }
    assert isinstance(link["id"], int)
    assert isinstance(link["product_id"], int)
    assert isinstance(link["supplier_id"], int)
    assert isinstance(link["product_name"], str)
    assert isinstance(link["supplier_name"], str)
    assert isinstance(link["purchase_price"], int)
    assert isinstance(link["margin_percent"], int)
    assert isinstance(link["floor_price"], int)
    assert isinstance(link["sale_price"], int)
    assert isinstance(link["quantity"], int)
    assert isinstance(link["quantity_unit"], str)
    assert isinstance(link["low_stock_threshold"], int)
    assert link["stock_status"] in {"available", "low", "out"}


def test_get_products_returns_empty_paginated_response():
    response = client.get("/products")

    assert response.status_code == 200

    data = response.json()
    assert_paginated_response(data)
    assert data["items"] == []
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 0
    assert data["total_pages"] == 0
    assert data["has_next"] is False
    assert data["has_previous"] is False


def test_post_products_creates_catalog_product_with_company_and_tags(db_session):
    suffix = unique_suffix()
    company = create_company(db_session, suffix)

    product = create_product(
        {
            "name": f"  Catalog product {suffix}  ",
            "company_id": company.id,
            "tags": ["Retail", "retail", "Warehouse"],
        }
    )

    assert_product_response_shape(product)
    assert product["name"] == f"Catalog product {suffix}"
    assert product["company_id"] == company.id
    assert product["company_name"] == company.name
    assert [tag["name"] for tag in product["tags"]] == ["retail", "warehouse"]
    assert product["supplier_links"] == []
    assert "purchase_price" not in product
    assert "supplier_id" not in product


def test_get_products_supports_name_search_and_returns_supplier_links(db_session):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    matching_product = create_product(
        {
            "name": f"Searchable product {suffix}",
            "tags": [],
        }
    )
    create_product(
        {
            "name": f"Unmatched product {suffix}",
            "tags": [],
        }
    )

    link_response = client.post(
        f"/products/{matching_product['id']}/links",
        json={
            "supplier_id": supplier.id,
            "purchase_price": 101,
            "margin_percent": 25,
            "quantity": 4,
            "quantity_unit": "шт",
            "low_stock_threshold": 5,
        },
    )

    assert link_response.status_code == 201

    response = client.get(
        "/products",
        params={"search": f"Searchable product {suffix}", "page_size": 10},
    )

    assert response.status_code == 200

    data = response.json()
    assert_paginated_response(data)
    assert data["total"] == 1
    assert len(data["items"]) == 1

    product = data["items"][0]
    assert_product_response_shape(product)
    assert product["id"] == matching_product["id"]
    assert len(product["supplier_links"]) == 1

    link = product["supplier_links"][0]
    assert_product_supplier_response_shape(link)
    assert link["product_id"] == matching_product["id"]
    assert link["supplier_id"] == supplier.id
    assert link["product_name"] == matching_product["name"]
    assert link["supplier_name"] == supplier.name


def test_post_product_link_calculates_prices_and_persists_inventory(db_session):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    product = create_product(
        {
            "name": f"Linked product {suffix}",
            "tags": [],
        }
    )

    response = client.post(
        f"/products/{product['id']}/links",
        json={
            "supplier_id": supplier.id,
            "purchase_price": 101,
            "margin_percent": 25,
            "quantity": 4,
            "quantity_unit": "шт",
            "low_stock_threshold": 5,
        },
    )

    assert response.status_code == 201

    link = response.json()
    assert_product_supplier_response_shape(link)
    assert link["product_id"] == product["id"]
    assert link["supplier_id"] == supplier.id
    assert link["product_name"] == product["name"]
    assert link["supplier_name"] == supplier.name
    assert link["purchase_price"] == 101
    assert link["margin_percent"] == 25
    assert link["floor_price"] == 127
    assert link["sale_price"] == 127
    assert link["quantity"] == 4
    assert link["quantity_unit"] == "шт"
    assert link["low_stock_threshold"] == 5
    assert link["stock_status"] == "low"

    stored_link = db_session.get(ProductSupplier, link["id"])
    assert stored_link is not None
    assert stored_link.product_id == product["id"]
    assert stored_link.supplier_id == supplier.id


def test_post_product_link_rejects_missing_product_and_supplier(db_session):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    product = create_product(
        {
            "name": f"Error product {suffix}",
            "tags": [],
        }
    )
    link_payload = {
        "supplier_id": supplier.id,
        "purchase_price": 100,
        "margin_percent": 10,
        "sale_price": 120,
    }

    missing_product_response = client.post(
        "/products/999999/links",
        json=link_payload,
    )

    assert missing_product_response.status_code == 404
    assert missing_product_response.json()["detail"] == "Product was not found."

    missing_supplier_response = client.post(
        f"/products/{product['id']}/links",
        json={**link_payload, "supplier_id": 999999},
    )

    assert missing_supplier_response.status_code == 404
    assert missing_supplier_response.json()["detail"] == "Supplier was not found."


def test_post_product_link_rejects_invalid_price_and_duplicate_link(db_session):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    product = create_product(
        {
            "name": f"Duplicate product {suffix}",
            "tags": [],
        }
    )
    link_payload = {
        "supplier_id": supplier.id,
        "purchase_price": 100,
        "margin_percent": 20,
        "sale_price": 130,
        "quantity": 0,
        "quantity_unit": "шт",
        "low_stock_threshold": 5,
    }

    invalid_price_response = client.post(
        f"/products/{product['id']}/links",
        json={**link_payload, "sale_price": 119},
    )

    assert invalid_price_response.status_code == 422

    first_response = client.post(
        f"/products/{product['id']}/links",
        json=link_payload,
    )
    duplicate_response = client.post(
        f"/products/{product['id']}/links",
        json=link_payload,
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
