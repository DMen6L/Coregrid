from datetime import datetime

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
                "TRUNCATE TABLE sales, product_tags, tags, stock_movement_lines, "
                "stock_movements, products, companies, suppliers "
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
    quantity_unit=None,
    low_stock_threshold=None,
    company_id=None,
    supplier_id=None,
    tags=None,
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
    if quantity_unit is not None:
        payload["quantity_unit"] = quantity_unit
    if low_stock_threshold is not None:
        payload["low_stock_threshold"] = low_stock_threshold
    if tags is not None:
        payload["tags"] = tags

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


def create_sale(note=None, lines=None):
    if lines is None:
        product = create_product()
        sale_lines = [
            {
                "product_id": product["id"],
                "quantity": 1,
                "unit_price": product["sale_price"],
            }
        ]
    else:
        sale_lines = lines
    payload = {
        "note": note,
        "lines": sale_lines,
    }
    response = client.post("/sales", json=payload)
    assert response.status_code == 201
    return response.json()


def set_stock_movement_created_at(movement_id, created_at):
    with SessionLocal() as session:
        session.execute(
            text(
                "UPDATE stock_movements "
                "SET created_at = :created_at "
                "WHERE id = :movement_id"
            ),
            {"movement_id": movement_id, "created_at": created_at},
        )
        session.commit()


def set_sale_created_at(sale_id, created_at):
    with SessionLocal() as session:
        session.execute(
            text(
                "UPDATE sales "
                "SET created_at = :created_at "
                "WHERE id = :sale_id"
            ),
            {"sale_id": sale_id, "created_at": created_at},
        )
        session.commit()


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
        json={
            "purchase_price": 150,
            "sale_price": 150,
            "quantity": 8,
            "quantity_unit": "м",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["purchase_price"] == 150
    assert patch_response.json()["margin_percent"] == 0
    assert patch_response.json()["floor_price"] == 150
    assert patch_response.json()["sale_price"] == 150
    assert patch_response.json()["quantity"] == 8
    assert patch_response.json()["quantity_unit"] == "м"
    assert patch_response.json()["company_id"] == company["id"]
    assert patch_response.json()["supplier_id"] == supplier["id"]
    assert patch_response.json()["company_name"] == company["name"]
    assert patch_response.json()["supplier_name"] == supplier["name"]

    list_response = client.get("/products")
    assert_page(list_response, [patch_response.json()])


def test_product_tags_can_be_created_read_updated_and_cleared():
    product = create_product(tags=["Кабель", "Расходник", "кабель"])

    assert [tag["name"] for tag in product["tags"]] == ["кабель", "расходник"]

    get_response = client.get(f"/products/{product['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == product

    keep_tags_response = client.patch(
        f"/products/{product['id']}",
        json={"quantity": 8},
    )
    assert keep_tags_response.status_code == 200
    assert keep_tags_response.json()["tags"] == product["tags"]

    replace_tags_response = client.patch(
        f"/products/{product['id']}",
        json={"tags": ["Сезон", "витрина"]},
    )
    assert replace_tags_response.status_code == 200
    assert [tag["name"] for tag in replace_tags_response.json()["tags"]] == [
        "витрина",
        "сезон",
    ]

    clear_tags_response = client.patch(
        f"/products/{product['id']}",
        json={"tags": []},
    )
    assert clear_tags_response.status_code == 200
    assert clear_tags_response.json()["tags"] == []


def test_tags_can_be_created_and_listed():
    product = create_product(tags=["Кабель", "Витрина"])
    cable_tag = next(tag for tag in product["tags"] if tag["name"] == "кабель")

    search_response = client.get("/tags?search=каб&page_size=10")
    assert_page(search_response, [cable_tag], page_size=10)

    create_response = client.post("/tags", json={"name": "Новинка"})
    assert create_response.status_code == 201
    assert create_response.json()["name"] == "новинка"

    duplicate_response = client.post("/tags", json={"name": "новинка"})
    assert_duplicate_error(duplicate_response)


def test_incoming_stock_movement_increases_product_quantity():
    product = create_product(
        quantity=5,
        quantity_unit="м",
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
    assert movement["lines"][0]["quantity_unit_snapshot"] == "м"

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["quantity"] == 9
    assert get_product_response.json()["quantity_unit"] == "м"


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


def test_stock_movement_line_snapshots_quantity_unit():
    product = create_product(quantity=5, quantity_unit="кг")
    movement = create_stock_movement(
        movement_type="out",
        lines=[{"product_id": product["id"], "quantity_delta": -2}],
    )

    assert movement["lines"][0]["quantity_unit_snapshot"] == "кг"

    update_response = client.patch(
        f"/products/{product['id']}",
        json={"quantity_unit": "г"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["quantity_unit"] == "г"

    history_response = client.get(f"/stock-movements/{movement['id']}")

    assert history_response.status_code == 200
    assert history_response.json()["lines"][0]["quantity_unit_snapshot"] == "кг"


def test_sale_create_decreases_stock_and_creates_linked_movement():
    product = create_product(
        name="Sale Workflow Product",
        sale_price=300,
        quantity=5,
        quantity_unit="м",
    )

    response = client.post(
        "/sales",
        json={
            "note": "Counter sale",
            "lines": [
                {
                    "product_id": product["id"],
                    "quantity": 2,
                    "unit_price": 250,
                }
            ],
        },
    )

    assert response.status_code == 201
    sale = response.json()
    assert sale["note"] == "Counter sale"
    assert sale["revenue"] == 500
    assert sale["stock_movement_id"] > 0
    assert len(sale["lines"]) == 1
    assert sale["lines"][0]["product_id"] == product["id"]
    assert sale["lines"][0]["quantity_delta"] == -2
    assert sale["lines"][0]["quantity_before"] == 5
    assert sale["lines"][0]["quantity_after"] == 3
    assert sale["lines"][0]["unit_price_snapshot"] == 250
    assert sale["lines"][0]["quantity_unit_snapshot"] == "м"

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["quantity"] == 3

    movement_response = client.get(f"/stock-movements/{sale['stock_movement_id']}")
    assert movement_response.status_code == 200
    assert movement_response.json()["movement_type"] == "out"
    assert movement_response.json()["note"] == "Counter sale"
    assert movement_response.json()["lines"] == sale["lines"]

    get_sale_response = client.get(f"/sales/{sale['id']}")
    assert get_sale_response.status_code == 200
    assert get_sale_response.json() == sale

    list_response = client.get("/sales")
    assert_page(list_response, [sale])


def test_sale_with_multiple_lines_updates_all_products():
    first_product = create_product(
        name="First Sale Product",
        sale_price=100,
        quantity=5,
    )
    second_product = create_product(
        name="Second Sale Product",
        purchase_price=200,
        sale_price=250,
        quantity=4,
        quantity_unit="кг",
    )

    sale = create_sale(
        lines=[
            {
                "product_id": first_product["id"],
                "quantity": 2,
                "unit_price": 90,
            },
            {
                "product_id": second_product["id"],
                "quantity": 3,
                "unit_price": 225,
            },
        ],
    )

    assert sale["revenue"] == 855
    assert [line["quantity_delta"] for line in sale["lines"]] == [-2, -3]
    assert [line["quantity_after"] for line in sale["lines"]] == [3, 1]
    assert [line["unit_price_snapshot"] for line in sale["lines"]] == [90, 225]
    assert [line["quantity_unit_snapshot"] for line in sale["lines"]] == ["шт", "кг"]


def test_sale_that_would_make_quantity_negative_is_rejected():
    product = create_product(quantity=2)

    response = client.post(
        "/sales",
        json={
            "lines": [
                {
                    "product_id": product["id"],
                    "quantity": 3,
                    "unit_price": product["sale_price"],
                }
            ]
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Sale would make product quantity negative"
    }

    get_product_response = client.get(f"/products/{product['id']}")
    assert get_product_response.status_code == 200
    assert get_product_response.json()["quantity"] == 2


def test_sale_missing_product_returns_not_found():
    response = client.post(
        "/sales",
        json={"lines": [{"product_id": 999, "quantity": 1, "unit_price": 100}]},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_stock_movement_out_does_not_create_sale():
    product = create_product(quantity=5)
    movement = create_stock_movement(
        movement_type="out",
        lines=[{"product_id": product["id"], "quantity_delta": -1}],
    )

    response = client.get("/sales")

    assert_page(response, [])
    assert movement["movement_type"] == "out"


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
    tagged_product = create_product(
        name="Tagged Product",
        quantity=7,
        tags=["Сервис"],
    )

    assert_page(
        client.get("/products?search=Searchable&page_size=10"),
        [available_product],
        page_size=10,
    )
    assert_page(
        client.get("/products?stock=available&page_size=10"),
        [available_product, low_product, tagged_product],
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
    assert_page(
        client.get("/products?search=сервис&page_size=10"),
        [tagged_product],
        page_size=10,
    )
    assert_page(
        client.get("/products?tag=сервис&page_size=10"),
        [tagged_product],
        page_size=10,
    )
    assert_page(
        client.get(f"/products?tag={tagged_product['tags'][0]['id']}&page_size=10"),
        [tagged_product],
        page_size=10,
    )


def test_product_pagination_supports_multiple_tag_filters():
    shared_product = create_product(
        name="Shared Tagged Product",
        tags=["Кабель", "Витрина"],
    )
    cable_product = create_product(
        name="Cable Product",
        tags=["Кабель", "Склад"],
    )
    display_product = create_product(
        name="Display Product",
        tags=["Витрина"],
    )

    assert_page(
        client.get("/products?tags=кабель&page_size=10"),
        [shared_product, cable_product],
        page_size=10,
    )
    assert_page(
        client.get("/products?tags=кабель&tags=витрина&page_size=10"),
        [shared_product],
        page_size=10,
    )
    assert_page(
        client.get("/products?search=Product&tags=витрина&page_size=10"),
        [shared_product, display_product],
        page_size=10,
    )
    assert_page(
        client.get("/products?tag=кабель&tags=витрина&page_size=10"),
        [shared_product],
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
        "out_of_stock": 1,
    }


def test_stock_movement_sales_summary_uses_outgoing_movements_in_date_range():
    product = create_product(
        name="Sale Product",
        sale_price=150,
        quantity=20,
    )
    second_product = create_product(
        name="Second Sale Product",
        purchase_price=200,
        sale_price=250,
        quantity=1,
        quantity_unit="мл",
    )
    included_sale = create_sale(
        lines=[
            {
                "product_id": product["id"],
                "quantity": 2,
                "unit_price": 140,
            },
            {
                "product_id": second_product["id"],
                "quantity": 1,
                "unit_price": 225,
            },
        ],
    )
    next_day_sale = create_sale(
        lines=[
            {
                "product_id": product["id"],
                "quantity": 3,
                "unit_price": 125,
            }
        ],
    )
    incoming_movement = create_stock_movement(
        movement_type="in",
        lines=[{"product_id": product["id"], "quantity_delta": 5}],
    )
    adjustment_movement = create_stock_movement(
        movement_type="adjustment",
        lines=[{"product_id": product["id"], "quantity_delta": -1}],
    )
    generic_outgoing_movement = create_stock_movement(
        movement_type="out",
        lines=[{"product_id": product["id"], "quantity_delta": -4}],
    )
    set_sale_created_at(
        included_sale["id"],
        datetime(2026, 7, 5, 10, 0),
    )
    set_sale_created_at(
        next_day_sale["id"],
        datetime(2026, 7, 6, 9, 0),
    )
    set_stock_movement_created_at(
        incoming_movement["id"],
        datetime(2026, 7, 5, 12, 0),
    )
    set_stock_movement_created_at(
        adjustment_movement["id"],
        datetime(2026, 7, 5, 13, 0),
    )
    set_stock_movement_created_at(
        generic_outgoing_movement["id"],
        datetime(2026, 7, 5, 14, 0),
    )

    one_day_response = client.get(
        "/stock-movements/sales-summary"
        "?date_from=2026-07-05&date_to=2026-07-05"
    )
    range_response = client.get(
        "/stock-movements/sales-summary"
        "?date_from=2026-07-05&date_to=2026-07-07"
    )

    assert one_day_response.status_code == 200
    assert one_day_response.json() == {
        "revenue": 505,
        "units_sold": 3,
        "units_sold_by_unit": [
            {"quantity_unit": "мл", "quantity": 1},
            {"quantity_unit": "шт", "quantity": 2},
        ],
        "daily_totals": [
            {
                "date": "2026-07-05",
                "revenue": 505,
                "units_sold": 3,
                "units_sold_by_unit": [
                    {"quantity_unit": "мл", "quantity": 1},
                    {"quantity_unit": "шт", "quantity": 2},
                ],
                "sale_operations": 1,
            },
        ],
        "best_sellers": [
            {
                "product_id": product["id"],
                "product_name": "Sale Product",
                "revenue": 280,
                "units_sold_by_unit": [
                    {"quantity_unit": "шт", "quantity": 2},
                ],
                "sale_operations": 1,
                "current_quantity": 15,
                "current_quantity_unit": "шт",
                "stock_status": "available",
            },
            {
                "product_id": second_product["id"],
                "product_name": "Second Sale Product",
                "revenue": 225,
                "units_sold_by_unit": [
                    {"quantity_unit": "мл", "quantity": 1},
                ],
                "sale_operations": 1,
                "current_quantity": 0,
                "current_quantity_unit": "мл",
                "stock_status": "out",
            },
        ],
        "sale_operations": 1,
        "date_from": "2026-07-05",
        "date_to": "2026-07-05",
    }
    assert range_response.status_code == 200
    assert range_response.json() == {
        "revenue": 880,
        "units_sold": 6,
        "units_sold_by_unit": [
            {"quantity_unit": "мл", "quantity": 1},
            {"quantity_unit": "шт", "quantity": 5},
        ],
        "daily_totals": [
            {
                "date": "2026-07-05",
                "revenue": 505,
                "units_sold": 3,
                "units_sold_by_unit": [
                    {"quantity_unit": "мл", "quantity": 1},
                    {"quantity_unit": "шт", "quantity": 2},
                ],
                "sale_operations": 1,
            },
            {
                "date": "2026-07-06",
                "revenue": 375,
                "units_sold": 3,
                "units_sold_by_unit": [
                    {"quantity_unit": "шт", "quantity": 3},
                ],
                "sale_operations": 1,
            },
            {
                "date": "2026-07-07",
                "revenue": 0,
                "units_sold": 0,
                "units_sold_by_unit": [],
                "sale_operations": 0,
            },
        ],
        "best_sellers": [
            {
                "product_id": product["id"],
                "product_name": "Sale Product",
                "revenue": 655,
                "units_sold_by_unit": [
                    {"quantity_unit": "шт", "quantity": 5},
                ],
                "sale_operations": 2,
                "current_quantity": 15,
                "current_quantity_unit": "шт",
                "stock_status": "available",
            },
            {
                "product_id": second_product["id"],
                "product_name": "Second Sale Product",
                "revenue": 225,
                "units_sold_by_unit": [
                    {"quantity_unit": "мл", "quantity": 1},
                ],
                "sale_operations": 1,
                "current_quantity": 0,
                "current_quantity_unit": "мл",
                "stock_status": "out",
            },
        ],
        "sale_operations": 2,
        "date_from": "2026-07-05",
        "date_to": "2026-07-07",
    }


def test_stock_movement_sales_summary_returns_zero_daily_totals_without_sales():
    response = client.get(
        "/stock-movements/sales-summary"
        "?date_from=2026-07-05&date_to=2026-07-06"
    )

    assert response.status_code == 200
    assert response.json() == {
        "revenue": 0,
        "units_sold": 0,
        "units_sold_by_unit": [],
        "daily_totals": [
            {
                "date": "2026-07-05",
                "revenue": 0,
                "units_sold": 0,
                "units_sold_by_unit": [],
                "sale_operations": 0,
            },
            {
                "date": "2026-07-06",
                "revenue": 0,
                "units_sold": 0,
                "units_sold_by_unit": [],
                "sale_operations": 0,
            },
        ],
        "best_sellers": [],
        "sale_operations": 0,
        "date_from": "2026-07-05",
        "date_to": "2026-07-06",
    }


def test_stock_movement_sales_summary_limits_best_sellers_and_orders_ties():
    sale_ids = []

    for index in range(6):
        product = create_product(
            name=f"Ranked Product {index + 1}",
            sale_price=100,
            quantity=2,
        )
        sale = create_sale(
            lines=[
                {
                    "product_id": product["id"],
                    "quantity": 1,
                    "unit_price": 100,
                }
            ]
        )
        sale_ids.append(sale["id"])

    for sale_id in sale_ids:
        set_sale_created_at(sale_id, datetime(2026, 7, 5, 10, 0))

    response = client.get(
        "/stock-movements/sales-summary"
        "?date_from=2026-07-05&date_to=2026-07-05"
    )

    assert response.status_code == 200
    best_sellers = response.json()["best_sellers"]
    assert len(best_sellers) == 5
    assert [item["product_id"] for item in best_sellers] == [1, 2, 3, 4, 5]


def test_stock_movement_sales_summary_rejects_invalid_date_range():
    response = client.get(
        "/stock-movements/sales-summary"
        "?date_from=2026-07-06&date_to=2026-07-05"
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "date_from cannot be after date_to"}


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
    assert_page(
        client.get("/stock-movements?page=1&page_size=2&order=latest"),
        [movements[2], movements[1]],
        total=3,
        page=1,
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
        "/sales?page=0",
        "/sales?page_size=101",
    ],
)
def test_pagination_query_validation_errors_return_unprocessable_entity(path):
    response = client.get(path)

    assert_validation_error(response)


def test_stock_movement_missing_rows_return_not_found():
    missing_movement_response = client.get("/stock-movements/999")
    missing_product_history_response = client.get("/products/999/movements")
    missing_sale_response = client.get("/sales/999")

    assert missing_movement_response.status_code == 404
    assert missing_movement_response.json() == {"detail": "Stock movement not found"}
    assert missing_product_history_response.status_code == 404
    assert missing_product_history_response.json() == {"detail": "Product not found"}
    assert missing_sale_response.status_code == 404
    assert missing_sale_response.json() == {"detail": "Sale not found"}


def test_product_can_be_created_without_company_or_supplier():
    product = create_product(quantity=0)

    assert product["company_id"] is None
    assert product["supplier_id"] is None
    assert product["quantity"] == 0
    assert product["quantity_unit"] == "шт"
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
    assert response.json()["quantity_unit"] == "шт"
    assert response.json()["low_stock_threshold"] == 5
    assert response.json()["stock_status"] == "out"


def test_product_create_accepts_and_strips_quantity_unit():
    response = client.post(
        "/products",
        json={
            "name": "Measured Product",
            "purchase_price": 100,
            "quantity": 12,
            "quantity_unit": "  мл  ",
        },
    )

    assert response.status_code == 201
    assert response.json()["quantity"] == 12
    assert response.json()["quantity_unit"] == "мл"


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
        (
            "/products",
            {
                "name": "Invalid Unit Product",
                "purchase_price": 100,
                "quantity_unit": "",
            },
        ),
        (
            "/products",
            {
                "name": "Invalid Unit Product",
                "purchase_price": 100,
                "quantity_unit": "x" * 21,
            },
        ),
        (
            "/products",
            {
                "name": "Invalid Tag Product",
                "purchase_price": 100,
                "tags": [""],
            },
        ),
        (
            "/products",
            {
                "name": "Invalid Tag Product",
                "purchase_price": 100,
                "tags": ["x" * 51],
            },
        ),
        ("/tags", {"name": ""}),
        ("/tags", {"name": "x" * 51}),
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
        ("/sales", {"lines": []}),
        ("/sales", {"lines": [{"product_id": 1, "quantity": 1}]}),
        (
            "/sales",
            {"lines": [{"product_id": 1, "quantity": 0, "unit_price": 100}]},
        ),
        (
            "/sales",
            {"lines": [{"product_id": 1, "quantity": -1, "unit_price": 100}]},
        ),
        (
            "/sales",
            {"lines": [{"product_id": 1, "quantity": 1, "unit_price": 0}]},
        ),
        (
            "/sales",
            {"lines": [{"product_id": 1, "quantity": 1, "unit_price": -1}]},
        ),
        (
            "/sales",
            {
                "lines": [
                    {"product_id": 1, "quantity": 1, "unit_price": 100},
                    {"product_id": 1, "quantity": 2, "unit_price": 100},
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
        ("/products/1", {"quantity_unit": ""}),
        ("/products/1", {"quantity_unit": "x" * 21}),
        ("/products/1", {"low_stock_threshold": -1}),
        ("/products/1", {"tags": [""]}),
        ("/products/1", {"tags": ["x" * 51]}),
    ],
)
def test_patch_validation_errors_return_unprocessable_entity(path, payload):
    response = client.patch(path, json=payload)

    assert_validation_error(response)


def test_patch_product_rejects_null_tags():
    product = create_product(tags=["existing"])

    response = client.patch(f"/products/{product['id']}", json={"tags": None})

    assert response.status_code == 422
    assert response.json() == {"detail": "tags cannot be null"}


def test_patch_product_rejects_null_quantity_unit():
    product = create_product()

    response = client.patch(
        f"/products/{product['id']}",
        json={"quantity_unit": None},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "quantity_unit cannot be null"}


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


def test_delete_product_removes_tag_links_but_keeps_tags():
    product = create_product(tags=["расходник"])
    tag = product["tags"][0]

    response = client.delete(f"/products/{product['id']}")

    assert response.status_code == 204
    assert_page(client.get("/tags"), [tag])
    assert_page(client.get("/products?tag=расходник"), [])


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
