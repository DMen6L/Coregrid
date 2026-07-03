import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from main import app


client = TestClient(app)


def truncate_database():
    with SessionLocal() as session:
        session.execute(
            text(
                "TRUNCATE TABLE products, companies, suppliers "
                "RESTART IDENTITY CASCADE"
            )
        )
        session.commit()


@pytest.fixture(autouse=True)
def clean_database():
    truncate_database()

    yield

    truncate_database()


def create_company(name="Test Company", iin="121212121212"):
    response = client.post("/companies", json={"name": name, "iin": iin})
    assert response.status_code == 201
    return response.json()


def create_supplier(name="Test Supplier", phone_number="777777777777"):
    response = client.post(
        "/suppliers",
        json={"name": name, "phone_number": phone_number},
    )
    assert response.status_code == 201
    return response.json()


def create_product(
    name="Test Product",
    price=100,
    quantity=5,
    company_id=None,
    supplier_id=None,
):
    payload = {
        "name": name,
        "price": price,
        "quantity": quantity,
        "company_id": company_id,
        "supplier_id": supplier_id,
    }
    response = client.post("/products", json=payload)
    assert response.status_code == 201
    return response.json()


def assert_validation_error(response):
    assert response.status_code == 422
    assert "detail" in response.json()


def assert_duplicate_error(response):
    assert response.status_code == 409
    assert response.json() == {"detail": "Duplicate value conflicts existing row"}


def assert_missing_reference_error(response):
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Referenced row does not exist or was changed"
    }


def test_root_returns_health_payload():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_company_create_read_update_and_list():
    company = create_company()

    get_response = client.get(f"/companies/{company['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == company

    patch_response = client.patch(
        f"/companies/{company['id']}",
        json={"name": "Updated Company"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Updated Company"
    assert patch_response.json()["iin"] == company["iin"]

    list_response = client.get("/companies")
    assert list_response.status_code == 200
    assert list_response.json() == [patch_response.json()]


def test_supplier_create_read_update_and_list():
    supplier = create_supplier()

    get_response = client.get(f"/suppliers/{supplier['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == supplier

    patch_response = client.patch(
        f"/suppliers/{supplier['id']}",
        json={"phone_number": "888888888888"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["phone_number"] == "888888888888"
    assert patch_response.json()["name"] == supplier["name"]

    list_response = client.get("/suppliers")
    assert list_response.status_code == 200
    assert list_response.json() == [patch_response.json()]


def test_product_create_read_update_and_list_with_related_rows():
    company = create_company()
    supplier = create_supplier()
    product = create_product(company_id=company["id"], supplier_id=supplier["id"])

    get_response = client.get(f"/products/{product['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == product

    patch_response = client.patch(
        f"/products/{product['id']}",
        json={"price": 150, "quantity": 8},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["price"] == 150
    assert patch_response.json()["quantity"] == 8
    assert patch_response.json()["company_id"] == company["id"]
    assert patch_response.json()["supplier_id"] == supplier["id"]

    list_response = client.get("/products")
    assert list_response.status_code == 200
    assert list_response.json() == [patch_response.json()]


def test_product_can_be_created_without_company_or_supplier():
    product = create_product(quantity=0)

    assert product["company_id"] is None
    assert product["supplier_id"] is None
    assert product["quantity"] == 0


def test_product_quantity_defaults_to_zero():
    response = client.post(
        "/products",
        json={"name": "Default Quantity Product", "price": 100},
    )

    assert response.status_code == 201
    assert response.json()["quantity"] == 0


def test_create_payload_whitespace_is_stripped():
    response = client.post(
        "/companies",
        json={"name": "  Trimmed Company  ", "iin": " 121212121212 "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Trimmed Company"
    assert response.json()["iin"] == "121212121212"


def test_company_duplicate_iin_returns_conflict():
    create_company(name="First Company", iin="121212121212")

    response = client.post(
        "/companies",
        json={"name": "Second Company", "iin": "121212121212"},
    )

    assert_duplicate_error(response)


def test_company_duplicate_name_returns_conflict():
    create_company(name="Duplicate Company", iin="121212121212")

    response = client.post(
        "/companies",
        json={"name": "Duplicate Company", "iin": "131313131313"},
    )

    assert_duplicate_error(response)


def test_supplier_duplicate_name_returns_conflict():
    create_supplier(name="Duplicate Supplier", phone_number="777777777777")

    response = client.post(
        "/suppliers",
        json={"name": "Duplicate Supplier", "phone_number": "888888888888"},
    )

    assert_duplicate_error(response)


def test_supplier_duplicate_phone_number_returns_conflict():
    create_supplier(name="First Supplier", phone_number="777777777777")

    response = client.post(
        "/suppliers",
        json={"name": "Second Supplier", "phone_number": "777777777777"},
    )

    assert_duplicate_error(response)


def test_patch_duplicate_company_value_returns_conflict():
    first_company = create_company(name="First Company", iin="121212121212")
    second_company = create_company(name="Second Company", iin="131313131313")

    response = client.patch(
        f"/companies/{second_company['id']}",
        json={"iin": first_company["iin"]},
    )

    assert_duplicate_error(response)


def test_product_missing_company_reference_returns_conflict():
    response = client.post(
        "/products",
        json={"name": "Missing Company Product", "price": 100, "company_id": 999},
    )

    assert_missing_reference_error(response)


def test_product_missing_supplier_reference_returns_conflict():
    response = client.post(
        "/products",
        json={"name": "Missing Supplier Product", "price": 100, "supplier_id": 999},
    )

    assert_missing_reference_error(response)


def test_patch_product_missing_company_reference_returns_conflict():
    product = create_product()

    response = client.patch(
        f"/products/{product['id']}",
        json={"company_id": 999},
    )

    assert_missing_reference_error(response)


def test_patch_product_missing_supplier_reference_returns_conflict():
    product = create_product()

    response = client.patch(
        f"/products/{product['id']}",
        json={"supplier_id": 999},
    )

    assert_missing_reference_error(response)


def test_patch_product_can_clear_company_and_supplier_relationships():
    company = create_company()
    supplier = create_supplier()
    product = create_product(company_id=company["id"], supplier_id=supplier["id"])

    response = client.patch(
        f"/products/{product['id']}",
        json={"company_id": None, "supplier_id": None},
    )

    assert response.status_code == 200
    assert response.json()["company_id"] is None
    assert response.json()["supplier_id"] is None


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/companies", {"name": "Invalid IIN Company", "iin": "123"}),
        ("/companies", {"name": "", "iin": "121212121212"}),
        ("/suppliers", {"name": "Invalid Supplier", "phone_number": "abc777777777777"}),
        ("/suppliers", {"name": "Invalid Supplier", "phone_number": "777"}),
        ("/products", {"name": "Invalid Price Product", "price": 0}),
        ("/products", {"name": "Invalid Price Product", "price": -1}),
        (
            "/products",
            {"name": "Invalid Quantity Product", "price": 100, "quantity": -1},
        ),
    ],
)
def test_create_validation_errors_return_unprocessable_entity(path, payload):
    response = client.post(path, json=payload)

    assert_validation_error(response)


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/companies/1", {"iin": "123"}),
        ("/suppliers/1", {"phone_number": "777"}),
        ("/products/1", {"price": 0}),
        ("/products/1", {"quantity": -1}),
    ],
)
def test_patch_validation_errors_return_unprocessable_entity(path, payload):
    response = client.patch(path, json=payload)

    assert_validation_error(response)


@pytest.mark.parametrize(
    "path",
    ["/companies/1", "/suppliers/1", "/products/1"],
)
def test_empty_patch_payload_returns_unprocessable_entity(path):
    response = client.patch(path, json={})

    assert_validation_error(response)


@pytest.mark.parametrize(
    ("path", "payload", "expected_detail"),
    [
        ("/companies/999", {"name": "Missing Company"}, "Company not found"),
        ("/suppliers/999", {"name": "Missing Supplier"}, "Supplier not found"),
        ("/products/999", {"name": "Missing Product"}, "Product not found"),
    ],
)
def test_patch_missing_row_returns_not_found(path, payload, expected_detail):
    response = client.patch(path, json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": expected_detail}


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/companies/999", "Company not found"),
        ("/suppliers/999", "Supplier not found"),
        ("/products/999", "Product not found"),
    ],
)
def test_get_missing_row_returns_not_found(path, expected_detail):
    response = client.get(path)

    assert response.status_code == 404
    assert response.json() == {"detail": expected_detail}


def test_delete_product_removes_product():
    product = create_product()

    response = client.delete(f"/products/{product['id']}")

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(f"/products/{product['id']}")
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Product not found"}


def test_delete_company_keeps_product_and_clears_company_id():
    company = create_company()
    supplier = create_supplier()
    product = create_product(company_id=company["id"], supplier_id=supplier["id"])

    response = client.delete(f"/companies/{company['id']}")

    assert response.status_code == 204
    assert response.content == b""

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["company_id"] is None
    assert get_product_response.json()["supplier_id"] == supplier["id"]

    get_company_response = client.get(f"/companies/{company['id']}")
    assert get_company_response.status_code == 404
    assert get_company_response.json() == {"detail": "Company not found"}


def test_delete_supplier_keeps_product_and_clears_supplier_id():
    company = create_company()
    supplier = create_supplier()
    product = create_product(company_id=company["id"], supplier_id=supplier["id"])

    response = client.delete(f"/suppliers/{supplier['id']}")

    assert response.status_code == 204
    assert response.content == b""

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["company_id"] == company["id"]
    assert get_product_response.json()["supplier_id"] is None

    get_supplier_response = client.get(f"/suppliers/{supplier['id']}")
    assert get_supplier_response.status_code == 404
    assert get_supplier_response.json() == {"detail": "Supplier not found"}


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/companies/999", "Company not found"),
        ("/suppliers/999", "Supplier not found"),
        ("/products/999", "Product not found"),
    ],
)
def test_delete_missing_row_returns_not_found(path, expected_detail):
    response = client.delete(path)

    assert response.status_code == 404
    assert response.json() == {"detail": expected_detail}
