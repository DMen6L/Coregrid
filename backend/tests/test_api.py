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
                "TRUNCATE TABLE stock_movement_lines, stock_movements, "
                "products, companies, suppliers "
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


def create_supplier(name="Test Supplier", phone_number="+77001234567"):
    response = client.post(
        "/suppliers",
        json={"name": name, "phone_number": phone_number},
    )
    assert response.status_code == 201
    return response.json()


def create_product(
    name="Test Product",
    purchase_price=100,
    margin_percent=0,
    sale_price=None,
    quantity=5,
    low_stock_threshold=None,
    company_id=None,
    supplier_id=None,
):
    payload = {
        "name": name,
        "purchase_price": purchase_price,
        "margin_percent": margin_percent,
        "quantity": quantity,
        "company_id": company_id,
        "supplier_id": supplier_id,
    }
    if sale_price is not None:
        payload["sale_price"] = sale_price
    if low_stock_threshold is not None:
        payload["low_stock_threshold"] = low_stock_threshold

    response = client.post("/products", json=payload)
    assert response.status_code == 201
    return response.json()


def create_stock_movement(movement_type="in", note=None, lines=None):
    movement_lines = lines or [
        {"product_id": create_product()["id"], "quantity_delta": 1}
    ]
    payload = {
        "movement_type": movement_type,
        "note": note,
        "lines": movement_lines,
    }
    response = client.post("/stock-movements", json=payload)
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


def assert_page(response, expected_items, total=None, page=1, page_size=25):
    expected_total = len(expected_items) if total is None else total
    expected_pages = (
        (expected_total + page_size - 1) // page_size if expected_total else 0
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": expected_items,
        "total": expected_total,
        "page": page,
        "page_size": page_size,
        "pages": expected_pages,
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
    assert_page(list_response, [patch_response.json()])


def test_supplier_create_read_update_and_list():
    supplier = create_supplier()

    get_response = client.get(f"/suppliers/{supplier['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == supplier

    patch_response = client.patch(
        f"/suppliers/{supplier['id']}",
        json={"phone_number": "87001234567"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["phone_number"] == "87001234567"
    assert patch_response.json()["name"] == supplier["name"]

    list_response = client.get("/suppliers")
    assert_page(list_response, [patch_response.json()])


def test_product_create_read_update_and_list_with_related_rows():
    company = create_company()
    supplier = create_supplier()
    product = create_product(company_id=company["id"], supplier_id=supplier["id"])

    get_response = client.get(f"/products/{product['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == product

    patch_response = client.patch(
        f"/products/{product['id']}",
        json={"purchase_price": 150, "sale_price": 150, "quantity": 8},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["purchase_price"] == 150
    assert patch_response.json()["margin_percent"] == 0
    assert patch_response.json()["floor_price"] == 150
    assert patch_response.json()["sale_price"] == 150
    assert patch_response.json()["quantity"] == 8
    assert patch_response.json()["company_id"] == company["id"]
    assert patch_response.json()["supplier_id"] == supplier["id"]
    assert patch_response.json()["company_name"] == company["name"]
    assert patch_response.json()["supplier_name"] == supplier["name"]

    list_response = client.get("/products")
    assert_page(list_response, [patch_response.json()])


def test_incoming_stock_movement_increases_product_quantity():
    product = create_product(
        quantity=5,
        purchase_price=250,
        margin_percent=20,
        sale_price=300,
    )

    response = client.post(
        "/stock-movements",
        json={
            "movement_type": "in",
            "note": "Restock",
            "lines": [{"product_id": product["id"], "quantity_delta": 4}],
        },
    )

    assert response.status_code == 201
    movement = response.json()
    assert movement["movement_type"] == "in"
    assert movement["note"] == "Restock"
    assert len(movement["lines"]) == 1
    assert movement["lines"][0]["product_id"] == product["id"]
    assert movement["lines"][0]["quantity_delta"] == 4
    assert movement["lines"][0]["quantity_before"] == 5
    assert movement["lines"][0]["quantity_after"] == 9
    assert movement["lines"][0]["unit_price_snapshot"] == 300

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["quantity"] == 9


def test_outgoing_stock_movement_decreases_product_quantity():
    product = create_product(quantity=5)

    response = client.post(
        "/stock-movements",
        json={
            "movement_type": "out",
            "lines": [{"product_id": product["id"], "quantity_delta": -3}],
        },
    )

    assert response.status_code == 201
    assert response.json()["lines"][0]["quantity_before"] == 5
    assert response.json()["lines"][0]["quantity_after"] == 2

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["quantity"] == 2


@pytest.mark.parametrize("quantity_delta", [3, -2])
def test_adjustment_stock_movement_can_increase_or_decrease_quantity(quantity_delta):
    product = create_product(quantity=5)

    response = client.post(
        "/stock-movements",
        json={
            "movement_type": "adjustment",
            "lines": [{"product_id": product["id"], "quantity_delta": quantity_delta}],
        },
    )

    assert response.status_code == 201
    assert response.json()["lines"][0]["quantity_before"] == 5
    assert response.json()["lines"][0]["quantity_after"] == 5 + quantity_delta

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["quantity"] == 5 + quantity_delta


def test_stock_movement_with_multiple_lines_updates_all_products():
    first_product = create_product(
        name="First Product",
        quantity=2,
        purchase_price=100,
        margin_percent=25,
        sale_price=125,
    )
    second_product = create_product(
        name="Second Product",
        quantity=7,
        purchase_price=300,
        margin_percent=10,
        sale_price=330,
    )

    response = client.post(
        "/stock-movements",
        json={
            "movement_type": "in",
            "note": "Delivery",
            "lines": [
                {"product_id": first_product["id"], "quantity_delta": 5},
                {"product_id": second_product["id"], "quantity_delta": 4},
            ],
        },
    )

    assert response.status_code == 201
    lines = response.json()["lines"]
    assert len(lines) == 2
    assert lines[0]["quantity_before"] == 2
    assert lines[0]["quantity_after"] == 7
    assert lines[0]["unit_price_snapshot"] == 125
    assert lines[1]["quantity_before"] == 7
    assert lines[1]["quantity_after"] == 11
    assert lines[1]["unit_price_snapshot"] == 330

    first_product_response = client.get(f"/products/{first_product['id']}")
    second_product_response = client.get(f"/products/{second_product['id']}")

    assert first_product_response.status_code == 200
    assert first_product_response.json()["quantity"] == 7
    assert second_product_response.status_code == 200
    assert second_product_response.json()["quantity"] == 11


def test_stock_movement_that_would_make_quantity_negative_is_rejected():
    product = create_product(quantity=2)

    response = client.post(
        "/stock-movements",
        json={
            "movement_type": "out",
            "lines": [{"product_id": product["id"], "quantity_delta": -3}],
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Stock movement would make product quantity negative"
    }

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["quantity"] == 2


def test_stock_movement_missing_product_returns_not_found():
    response = client.post(
        "/stock-movements",
        json={
            "movement_type": "in",
            "lines": [{"product_id": 999, "quantity_delta": 1}],
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_stock_movement_history_can_be_fetched():
    product = create_product(quantity=5)
    movement = create_stock_movement(
        movement_type="in",
        note="Delivery",
        lines=[{"product_id": product["id"], "quantity_delta": 2}],
    )

    list_response = client.get("/stock-movements")
    assert_page(list_response, [movement])

    get_response = client.get(f"/stock-movements/{movement['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == movement

    product_history_response = client.get(f"/products/{product['id']}/movements")
    assert_page(product_history_response, [movement])


def test_collection_pagination_limits_results():
    companies = [
        create_company(name=f"Company {index}", iin=f"10000000000{index}")
        for index in range(1, 4)
    ]
    suppliers = [
        create_supplier(name=f"Supplier {index}", phone_number=f"8700000000{index}")
        for index in range(1, 4)
    ]
    products = [
        create_product(name=f"Product {index}", quantity=index)
        for index in range(1, 4)
    ]

    assert_page(
        client.get("/companies?page=2&page_size=2"),
        [companies[2]],
        total=3,
        page=2,
        page_size=2,
    )
    assert_page(
        client.get("/suppliers?page=2&page_size=2"),
        [suppliers[2]],
        total=3,
        page=2,
        page_size=2,
    )
    assert_page(
        client.get("/products?page=2&page_size=2"),
        [products[2]],
        total=3,
        page=2,
        page_size=2,
    )


def test_product_pagination_supports_search_and_stock_filter():
    company = create_company(name="Searchable Company", iin="121212121212")
    supplier = create_supplier(name="Searchable Supplier", phone_number="+77001234567")
    available_product = create_product(
        name="Available Product",
        quantity=10,
        company_id=company["id"],
        supplier_id=supplier["id"],
    )
    low_product = create_product(
        name="Low Product",
        quantity=2,
        low_stock_threshold=5,
    )
    empty_product = create_product(name="Empty Product", quantity=0)

    assert_page(
        client.get("/products?search=Searchable&page_size=10"),
        [available_product],
        page_size=10,
    )
    assert_page(
        client.get("/products?stock=available&page_size=10"),
        [available_product, low_product],
        page_size=10,
    )
    assert_page(
        client.get("/products?stock=low&page_size=10"),
        [low_product],
        page_size=10,
    )
    assert_page(
        client.get("/products?stock=empty&page_size=10"),
        [empty_product],
        page_size=10,
    )


def test_product_summary_returns_global_inventory_totals():
    create_product(
        name="Low Product",
        purchase_price=100,
        sale_price=150,
        quantity=5,
        low_stock_threshold=5,
    )
    create_product(
        name="Available Product",
        purchase_price=50,
        sale_price=75,
        quantity=10,
    )
    create_product(name="Empty Product", purchase_price=200, quantity=0)

    response = client.get("/products/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_products": 3,
        "total_units": 15,
        "inventory_value": 1000,
        "low_stock": 1,
    }


def test_stock_movement_pagination_limits_history_results():
    product = create_product(quantity=0)
    movements = [
        create_stock_movement(
            movement_type="in",
            note=f"Delivery {index}",
            lines=[{"product_id": product["id"], "quantity_delta": 1}],
        )
        for index in range(1, 4)
    ]

    assert_page(
        client.get("/stock-movements?page=2&page_size=2"),
        [movements[2]],
        total=3,
        page=2,
        page_size=2,
    )
    assert_page(
        client.get(f"/products/{product['id']}/movements?page=2&page_size=2"),
        [movements[2]],
        total=3,
        page=2,
        page_size=2,
    )


@pytest.mark.parametrize(
    "path",
    [
        "/companies?page=0",
        "/suppliers?page_size=101",
        "/products?page=0",
        "/products?page_size=101",
        "/products?stock=invalid",
        "/stock-movements?page=0",
        "/products/1/movements?page_size=101",
    ],
)
def test_pagination_query_validation_errors_return_unprocessable_entity(path):
    response = client.get(path)

    assert_validation_error(response)


def test_stock_movement_missing_rows_return_not_found():
    missing_movement_response = client.get("/stock-movements/999")
    missing_product_history_response = client.get("/products/999/movements")

    assert missing_movement_response.status_code == 404
    assert missing_movement_response.json() == {"detail": "Stock movement not found"}
    assert missing_product_history_response.status_code == 404
    assert missing_product_history_response.json() == {"detail": "Product not found"}


def test_product_can_be_created_without_company_or_supplier():
    product = create_product(quantity=0)

    assert product["company_id"] is None
    assert product["supplier_id"] is None
    assert product["quantity"] == 0
    assert product["stock_status"] == "out"


def test_product_quantity_and_low_stock_threshold_defaults():
    response = client.post(
        "/products",
        json={"name": "Default Quantity Product", "purchase_price": 100},
    )

    assert response.status_code == 201
    assert response.json()["purchase_price"] == 100
    assert response.json()["margin_percent"] == 0
    assert response.json()["floor_price"] == 100
    assert response.json()["sale_price"] == 100
    assert response.json()["quantity"] == 0
    assert response.json()["low_stock_threshold"] == 5
    assert response.json()["stock_status"] == "out"


def test_product_create_calculates_floor_price_and_defaults_sale_price():
    response = client.post(
        "/products",
        json={
            "name": "Priced Product",
            "purchase_price": 4999,
            "margin_percent": 10,
        },
    )

    assert response.status_code == 201
    assert response.json()["purchase_price"] == 4999
    assert response.json()["margin_percent"] == 10
    assert response.json()["floor_price"] == 5499
    assert response.json()["sale_price"] == 5499


def test_product_create_accepts_sale_price_above_floor_price():
    response = client.post(
        "/products",
        json={
            "name": "Rounded Product",
            "purchase_price": 4999,
            "margin_percent": 10,
            "sale_price": 5500,
        },
    )

    assert response.status_code == 201
    assert response.json()["floor_price"] == 5499
    assert response.json()["sale_price"] == 5500


def test_product_create_rejects_sale_price_below_floor_price():
    response = client.post(
        "/products",
        json={
            "name": "Underpriced Product",
            "purchase_price": 4999,
            "margin_percent": 10,
            "sale_price": 5498,
        },
    )

    assert_validation_error(response)


def test_patch_product_recalculates_floor_price_and_validates_sale_price():
    product = create_product(purchase_price=100, margin_percent=10, sale_price=110)

    rejected_response = client.patch(
        f"/products/{product['id']}",
        json={"margin_percent": 20},
    )

    assert rejected_response.status_code == 422
    assert rejected_response.json() == {
        "detail": "sale_price cannot be lower than floor_price"
    }

    accepted_response = client.patch(
        f"/products/{product['id']}",
        json={"margin_percent": 20, "sale_price": 120},
    )

    assert accepted_response.status_code == 200
    assert accepted_response.json()["margin_percent"] == 20
    assert accepted_response.json()["floor_price"] == 120
    assert accepted_response.json()["sale_price"] == 120


def test_product_create_accepts_custom_low_stock_threshold():
    product = create_product(quantity=8, low_stock_threshold=10)

    assert product["low_stock_threshold"] == 10
    assert product["stock_status"] == "low"


def test_patch_product_updates_low_stock_threshold_and_stock_status():
    product = create_product(quantity=8)

    response = client.patch(
        f"/products/{product['id']}",
        json={"low_stock_threshold": 10},
    )

    assert response.status_code == 200
    assert response.json()["low_stock_threshold"] == 10
    assert response.json()["stock_status"] == "low"


@pytest.mark.parametrize(
    ("quantity", "low_stock_threshold", "expected_status"),
    [
        (0, 5, "out"),
        (3, 5, "low"),
        (6, 5, "available"),
        (3, 0, "available"),
    ],
)
def test_product_response_includes_calculated_stock_status(
    quantity,
    low_stock_threshold,
    expected_status,
):
    product = create_product(
        quantity=quantity,
        low_stock_threshold=low_stock_threshold,
    )

    assert product["stock_status"] == expected_status


def test_stock_movement_updates_later_product_stock_status():
    product = create_product(quantity=8, low_stock_threshold=5)

    response = client.post(
        "/stock-movements",
        json={
            "movement_type": "out",
            "lines": [{"product_id": product["id"], "quantity_delta": -4}],
        },
    )

    assert response.status_code == 201

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["quantity"] == 4
    assert get_product_response.json()["stock_status"] == "low"


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
    create_supplier(name="Duplicate Supplier", phone_number="+77001234567")

    response = client.post(
        "/suppliers",
        json={"name": "Duplicate Supplier", "phone_number": "87001234567"},
    )

    assert_duplicate_error(response)


def test_supplier_duplicate_phone_number_returns_conflict():
    create_supplier(name="First Supplier", phone_number="+77001234567")

    response = client.post(
        "/suppliers",
        json={"name": "Second Supplier", "phone_number": "+77001234567"},
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
        json={
            "name": "Missing Company Product",
            "purchase_price": 100,
            "company_id": 999,
        },
    )

    assert_missing_reference_error(response)


def test_product_missing_supplier_reference_returns_conflict():
    response = client.post(
        "/products",
        json={
            "name": "Missing Supplier Product",
            "purchase_price": 100,
            "supplier_id": 999,
        },
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
        ("/products", {"name": "Invalid Price Product", "purchase_price": 0}),
        ("/products", {"name": "Invalid Price Product", "purchase_price": -1}),
        (
            "/products",
            {
                "name": "Invalid Margin Product",
                "purchase_price": 100,
                "margin_percent": -1,
            },
        ),
        (
            "/products",
            {
                "name": "Invalid Sale Product",
                "purchase_price": 100,
                "sale_price": 0,
            },
        ),
        (
            "/products",
            {
                "name": "Invalid Quantity Product",
                "purchase_price": 100,
                "quantity": -1,
            },
        ),
        (
            "/products",
            {
                "name": "Invalid Threshold Product",
                "purchase_price": 100,
                "low_stock_threshold": -1,
            },
        ),
        ("/stock-movements", {"movement_type": "transfer", "lines": []}),
        ("/stock-movements", {"movement_type": "in", "lines": []}),
        (
            "/stock-movements",
            {"movement_type": "in", "lines": [{"product_id": 1, "quantity_delta": 0}]},
        ),
        (
            "/stock-movements",
            {"movement_type": "in", "lines": [{"product_id": 1, "quantity_delta": -1}]},
        ),
        (
            "/stock-movements",
            {"movement_type": "out", "lines": [{"product_id": 1, "quantity_delta": 1}]},
        ),
        (
            "/stock-movements",
            {
                "movement_type": "in",
                "lines": [
                    {"product_id": 1, "quantity_delta": 1},
                    {"product_id": 1, "quantity_delta": 2},
                ],
            },
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
        ("/products/1", {"purchase_price": 0}),
        ("/products/1", {"margin_percent": -1}),
        ("/products/1", {"sale_price": 0}),
        ("/products/1", {"quantity": -1}),
        ("/products/1", {"low_stock_threshold": -1}),
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


def test_delete_product_with_stock_movement_history_returns_conflict():
    product = create_product()
    create_stock_movement(
        movement_type="in",
        lines=[{"product_id": product["id"], "quantity_delta": 1}],
    )

    response = client.delete(f"/products/{product['id']}")

    assert_missing_reference_error(response)

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200


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
