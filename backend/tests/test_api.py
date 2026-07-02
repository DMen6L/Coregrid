import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    response = client.delete("/cleanup")
    assert response.status_code == 204

    yield

    response = client.delete("/cleanup")
    assert response.status_code == 204


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


def test_cleanup_returns_no_content():
    create_company()
    create_supplier()
    create_product()

    response = client.delete("/cleanup")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/companies").json() == []
    assert client.get("/suppliers").json() == []
    assert client.get("/products").json() == []
