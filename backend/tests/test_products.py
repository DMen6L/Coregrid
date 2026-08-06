from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Company, Product, ProductSupplier, Supplier
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


def create_supplier(db_session, suffix: str, name: str | None = None) -> Supplier:
    supplier = Supplier(
        name=name or f"Product test supplier {suffix}",
        phone_number=unique_phone_number(),
    )

    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)

    return supplier


def create_product_model(
    db_session,
    suffix: str,
    *,
    name: str | None = None,
    company: Company | None = None,
    quantity_unit: str = "шт",
    low_stock_threshold: int = 5,
) -> Product:
    product = Product(
        name=name or f"Product test item {suffix}",
        company=company or create_company(db_session, suffix),
        quantity_unit=quantity_unit,
        low_stock_threshold=low_stock_threshold,
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    return product


def create_product_supplier_link(
    db_session,
    product: Product,
    supplier: Supplier,
    *,
    purchase_price: int = 100,
    margin_percent: int = 20,
    sale_price: int = 125,
    quantity: int = 4,
) -> ProductSupplier:
    link = ProductSupplier(
        product=product,
        supplier=supplier,
        purchase_price=purchase_price,
        margin_percent=margin_percent,
        sale_price=sale_price,
        quantity=quantity,
    )

    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)

    return link


def create_product(payload: dict) -> dict:
    response = client.post("/products", json=payload)

    assert response.status_code == 201
    return response.json()


def create_product_atomic(payload: dict) -> dict:
    response = client.post("/products/full", json=payload)

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


def assert_product_summary_response_shape(product: dict) -> None:
    assert set(product) == {
        "id",
        "name",
        "created_at",
        "quantity_unit",
        "low_stock_threshold",
        "company_name",
        "tags",
        "suppliers_count",
        "total_quantity",
        "min_purchase_price",
        "margin_percent",
        "min_sale_price",
        "stock_status",
    }
    assert isinstance(product["id"], int)
    assert isinstance(product["name"], str)
    assert datetime.fromisoformat(product["created_at"])
    assert isinstance(product["quantity_unit"], str)
    assert isinstance(product["low_stock_threshold"], int)
    assert isinstance(product["company_name"], str)
    assert isinstance(product["tags"], list)
    assert isinstance(product["suppliers_count"], int)
    assert isinstance(product["total_quantity"], int)
    assert product["min_purchase_price"] is None or isinstance(
        product["min_purchase_price"], int
    )
    assert product["margin_percent"] is None or isinstance(
        product["margin_percent"], int
    )
    assert product["min_sale_price"] is None or isinstance(product["min_sale_price"], int)
    assert product["stock_status"] in {"available", "low", "out", "none"}


def assert_product_response_shape(product: dict) -> None:
    assert set(product) == {
        "id",
        "name",
        "created_at",
        "company_id",
        "company_name",
        "quantity_unit",
        "low_stock_threshold",
        "tags",
        "supplier_links",
    }
    assert isinstance(product["id"], int)
    assert isinstance(product["name"], str)
    assert datetime.fromisoformat(product["created_at"])
    assert isinstance(product["company_id"], int)
    assert isinstance(product["company_name"], str)
    assert isinstance(product["quantity_unit"], str)
    assert isinstance(product["low_stock_threshold"], int)
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


def test_post_products_creates_catalog_product_with_company_and_stock_fields(
    db_session,
):
    suffix = unique_suffix()
    company = create_company(db_session, suffix)

    product = create_product(
        {
            "name": f"  Catalog product {suffix}  ",
            "company_id": company.id,
            "tags": ["Retail", "retail", "Warehouse"],
            "quantity_unit": "уп",
            "low_stock_threshold": 3,
        }
    )

    assert_product_response_shape(product)
    assert product["name"] == f"Catalog product {suffix}"
    assert product["company_id"] == company.id
    assert product["company_name"] == company.name
    assert product["quantity_unit"] == "уп"
    assert product["low_stock_threshold"] == 3
    assert [tag["name"] for tag in product["tags"]] == ["retail", "warehouse"]
    assert product["supplier_links"] == []
    assert "purchase_price" not in product
    assert "supplier_id" not in product


def test_get_products_supports_name_search_and_returns_summaries(db_session):
    suffix = unique_suffix()
    company = create_company(db_session, suffix)
    supplier = create_supplier(db_session, suffix)
    matching_product = create_product_model(
        db_session,
        suffix,
        name=f"Searchable product {suffix}",
        company=company,
        low_stock_threshold=2,
    )
    create_product_model(
        db_session,
        suffix,
        name=f"Unmatched product {suffix}",
        company=company,
    )
    create_product_supplier_link(
        db_session,
        matching_product,
        supplier,
        purchase_price=101,
        margin_percent=25,
        sale_price=127,
        quantity=4,
    )

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
    assert_product_summary_response_shape(product)
    assert product["id"] == matching_product.id
    assert product["name"] == matching_product.name
    assert product["company_name"] == company.name
    assert product["quantity_unit"] == "шт"
    assert product["low_stock_threshold"] == 2
    assert product["suppliers_count"] == 1
    assert product["total_quantity"] == 4
    assert product["min_purchase_price"] == 101
    assert product["margin_percent"] == 25
    assert product["min_sale_price"] == 127
    assert product["stock_status"] == "available"


def test_get_product_by_id_returns_detail_with_supplier_links(db_session):
    suffix = unique_suffix()
    company = create_company(db_session, suffix)
    first_supplier = create_supplier(db_session, suffix, name=f"First supplier {suffix}")
    second_supplier = create_supplier(db_session, suffix, name=f"Second supplier {suffix}")
    other_supplier = create_supplier(db_session, suffix, name=f"Other supplier {suffix}")
    product = create_product_model(
        db_session,
        suffix,
        name=f"Detailed product {suffix}",
        company=company,
        quantity_unit="кг",
        low_stock_threshold=7,
    )
    other_product = create_product_model(
        db_session,
        suffix,
        name=f"Other detailed product {suffix}",
        company=company,
    )
    first_link = create_product_supplier_link(
        db_session,
        product,
        first_supplier,
        purchase_price=100,
        margin_percent=20,
        sale_price=125,
        quantity=10,
    )
    second_link = create_product_supplier_link(
        db_session,
        product,
        second_supplier,
        purchase_price=90,
        margin_percent=30,
        sale_price=117,
        quantity=0,
    )
    create_product_supplier_link(
        db_session,
        other_product,
        other_supplier,
        purchase_price=50,
        margin_percent=10,
        sale_price=55,
        quantity=99,
    )

    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200

    data = response.json()
    assert_product_response_shape(data)
    assert data["id"] == product.id
    assert data["name"] == product.name
    assert data["company_id"] == company.id
    assert data["company_name"] == company.name
    assert data["quantity_unit"] == "кг"
    assert data["low_stock_threshold"] == 7

    links = data["supplier_links"]
    assert [link["id"] for link in links] == [first_link.id, second_link.id]

    first_link_data = links[0]
    assert_product_supplier_response_shape(first_link_data)
    assert first_link_data["product_id"] == product.id
    assert first_link_data["supplier_id"] == first_supplier.id
    assert first_link_data["product_name"] == product.name
    assert first_link_data["supplier_name"] == first_supplier.name
    assert first_link_data["purchase_price"] == 100
    assert first_link_data["margin_percent"] == 20
    assert first_link_data["floor_price"] == 120
    assert first_link_data["sale_price"] == 125
    assert first_link_data["quantity"] == 10
    assert first_link_data["stock_status"] == "available"

    second_link_data = links[1]
    assert_product_supplier_response_shape(second_link_data)
    assert second_link_data["supplier_id"] == second_supplier.id
    assert second_link_data["quantity"] == 0
    assert second_link_data["stock_status"] == "out"


def test_get_product_by_id_returns_empty_supplier_links_for_unlinked_product(
    db_session,
):
    suffix = unique_suffix()
    product = create_product_model(db_session, suffix)

    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200

    data = response.json()
    assert_product_response_shape(data)
    assert data["id"] == product.id
    assert data["supplier_links"] == []


def test_get_product_by_id_returns_404_for_missing_product():
    response = client.get("/products/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "product with such id does not exist."


def test_post_product_link_calculates_prices_and_persists_inventory(db_session):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    product = create_product_model(db_session, suffix)

    response = client.post(
        f"/products/{product.id}/links",
        json=[
            {
                "supplier_id": supplier.id,
                "purchase_price": 101,
                "margin_percent": 25,
                "quantity": 4,
            }
        ],
    )

    assert response.status_code == 201

    links = response.json()
    assert len(links) == 1

    link = links[0]
    assert_product_supplier_response_shape(link)
    assert link["product_id"] == product.id
    assert link["supplier_id"] == supplier.id
    assert link["product_name"] == product.name
    assert link["supplier_name"] == supplier.name
    assert link["purchase_price"] == 101
    assert link["margin_percent"] == 25
    assert link["floor_price"] == 127
    assert link["sale_price"] == 127
    assert link["quantity"] == 4
    assert link["stock_status"] == "low"

    stored_link = db_session.get(ProductSupplier, link["id"])
    assert stored_link is not None
    assert stored_link.product_id == product.id
    assert stored_link.supplier_id == supplier.id


def test_post_product_link_rejects_missing_product_and_supplier(db_session):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    product = create_product_model(db_session, suffix)
    link_payload = {
        "supplier_id": supplier.id,
        "purchase_price": 100,
        "margin_percent": 10,
        "sale_price": 120,
    }

    missing_product_response = client.post(
        "/products/999999/links",
        json=[link_payload],
    )

    assert missing_product_response.status_code == 404
    assert (
        missing_product_response.json()["detail"]
        == "No product with such id in the database."
    )

    missing_supplier_response = client.post(
        f"/products/{product.id}/links",
        json=[{**link_payload, "supplier_id": 999999}],
    )

    assert missing_supplier_response.status_code == 404
    assert missing_supplier_response.json()["detail"] == {
        "message": "One or more suppliers were not found.",
        "supplier_ids": [999999],
    }


def test_post_product_link_rejects_invalid_price_and_duplicate_link(db_session):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    product = create_product_model(db_session, suffix)
    link_payload = {
        "supplier_id": supplier.id,
        "purchase_price": 100,
        "margin_percent": 20,
        "sale_price": 130,
        "quantity": 0,
    }

    invalid_price_response = client.post(
        f"/products/{product.id}/links",
        json=[{**link_payload, "sale_price": 119}],
    )

    assert invalid_price_response.status_code == 422

    first_response = client.post(
        f"/products/{product.id}/links",
        json=[link_payload],
    )
    duplicate_response = client.post(
        f"/products/{product.id}/links",
        json=[link_payload],
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


def test_post_product_full_creates_product_company_supplier_and_link_atomically(
    db_session,
):
    suffix = unique_suffix()
    supplier_phone_number = unique_phone_number()

    product = create_product_atomic(
        {
            "product_name": f"Atomic product {suffix}",
            "company": {
                "name": f"Atomic company {suffix}",
                "iin": f"{uuid4().int % 1_000_000_000_000:012d}",
            },
            "tags": ["Atomic", "atomic", "Featured"],
            "quantity_unit": "box",
            "low_stock_threshold": 3,
            "product_links": [
                {
                    "supplier": {
                        "name": f"Atomic supplier {suffix}",
                        "phone_number": supplier_phone_number,
                    },
                    "purchase_price": 100,
                    "margin_percent": 25,
                    "quantity": 7,
                }
            ],
        }
    )

    assert_product_response_shape(product)
    assert product["name"] == f"Atomic product {suffix}"
    assert product["company_name"] == f"Atomic company {suffix}"
    assert product["quantity_unit"] == "box"
    assert product["low_stock_threshold"] == 3
    assert [tag["name"] for tag in product["tags"]] == ["atomic", "featured"]

    links = product["supplier_links"]
    assert len(links) == 1

    link = links[0]
    assert_product_supplier_response_shape(link)
    assert link["product_id"] == product["id"]
    assert link["supplier_name"] == f"Atomic supplier {suffix}"
    assert link["purchase_price"] == 100
    assert link["margin_percent"] == 25
    assert link["floor_price"] == 125
    assert link["sale_price"] == 125
    assert link["quantity"] == 7
    assert link["stock_status"] == "available"

    stored_product = db_session.get(Product, product["id"])
    stored_link = db_session.get(ProductSupplier, link["id"])
    stored_supplier = db_session.get(Supplier, link["supplier_id"])

    assert stored_product is not None
    assert stored_link is not None
    assert stored_supplier is not None
    assert stored_supplier.phone_number == supplier_phone_number


def test_post_product_full_rejects_duplicate_product_identity(db_session):
    suffix = unique_suffix()
    company = create_company(db_session, suffix)
    supplier = create_supplier(db_session, suffix)
    existing_product = create_product_model(
        db_session,
        suffix,
        name=f"Atomic duplicate product {suffix}",
        company=company,
        quantity_unit="шт",
    )

    response = client.post(
        "/products/full",
        json={
            "product_name": existing_product.name,
            "company_id": company.id,
            "quantity_unit": "шт",
            "product_links": [
                {
                    "supplier_id": supplier.id,
                    "purchase_price": 100,
                    "margin_percent": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Violated unique constraint: uq_products_name_company_unit"
    )


def test_post_product_full_rejects_duplicate_new_company(db_session):
    suffix = unique_suffix()
    company = create_company(db_session, suffix)

    response = client.post(
        "/products/full",
        json={
            "product_name": f"Atomic company duplicate product {suffix}",
            "company": {
                "name": company.name,
                "iin": f"{uuid4().int % 1_000_000_000_000:012d}",
            },
            "product_links": [
                {
                    "supplier": {
                        "name": f"Atomic company duplicate supplier {suffix}",
                        "phone_number": unique_phone_number(),
                    },
                    "purchase_price": 100,
                    "margin_percent": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Violated unique constraint: uq_companies_name"

    stored_product_id = db_session.scalar(
        select(Product.id).where(
            Product.name == f"Atomic company duplicate product {suffix}"
        )
    )
    assert stored_product_id is None


def test_post_product_full_rejects_duplicate_new_supplier_and_rolls_back_product(
    db_session,
):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    product_name = f"Atomic supplier duplicate product {suffix}"

    response = client.post(
        "/products/full",
        json={
            "product_name": product_name,
            "company": {
                "name": f"Atomic supplier duplicate company {suffix}",
                "iin": f"{uuid4().int % 1_000_000_000_000:012d}",
            },
            "product_links": [
                {
                    "supplier": {
                        "name": supplier.name,
                        "phone_number": unique_phone_number(),
                    },
                    "purchase_price": 100,
                    "margin_percent": 20,
                    "quantity": 1,
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Violated unique constraint: uq_suppliers_name"

    stored_product_id = db_session.scalar(
        select(Product.id).where(Product.name == product_name)
    )
    assert stored_product_id is None


def test_post_product_full_rejects_duplicate_product_supplier_links(db_session):
    suffix = unique_suffix()
    supplier = create_supplier(db_session, suffix)
    product_name = f"Atomic duplicate link product {suffix}"

    response = client.post(
        "/products/full",
        json={
            "product_name": product_name,
            "company": {
                "name": f"Atomic duplicate link company {suffix}",
                "iin": f"{uuid4().int % 1_000_000_000_000:012d}",
            },
            "product_links": [
                {
                    "supplier_id": supplier.id,
                    "purchase_price": 100,
                    "margin_percent": 20,
                    "quantity": 1,
                },
                {
                    "supplier_id": supplier.id,
                    "purchase_price": 110,
                    "margin_percent": 20,
                    "quantity": 2,
                },
            ],
        },
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Violated unique constraint: uq_product_suppliers_product_supplier"
    )

    stored_product_id = db_session.scalar(
        select(Product.id).where(Product.name == product_name)
    )
    assert stored_product_id is None
