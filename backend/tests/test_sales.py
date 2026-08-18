from fastapi import status
import pytest


def test_add_sale(
    client,
    auth_headers,
    workspace,
    product_supplier_link,
) -> None:
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
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"]
    assert data["note"] == payload["note"]
    assert len(data["lines"]) == 1

    line = data["lines"][0]
    assert line["product_supplier_id"] == product_supplier_link["id"]
    assert line["sale_quantity"] == 2
    assert line["unit_cost_snapshot"] == 100
    assert line["unit_sale_price_snapshot"] == 130
    assert line["quantity_unit_snapshot"] == "шт"


def test_get_sales(client, auth_headers, workspace, sale) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/sales",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 1
    assert data["total_pages"] == 1
    assert data["has_next"] is False
    assert data["has_previous"] is False

    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["id"] == sale["id"]
    assert item["note"] == sale["note"]
    assert item["revenue"] == 260
    assert item["lines_count"] == 1


def test_get_sale_by_id(client, auth_headers, workspace, sale) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/sales/{sale['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == sale["id"]
    assert data["note"] == sale["note"]
    assert len(data["lines"]) == 1


def test_get_sale_by_id_not_found_error(
    client,
    auth_headers,
    workspace,
    sale,
) -> None:
    not_found_id = sale["id"] + 999
    response = client.get(
        f"/workspaces/{workspace['id']}/sales/{not_found_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_sale_missing_product_supplier_error(
    client,
    auth_headers,
    workspace,
) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/sales",
        headers=auth_headers,
        json={
            "note": "missing link",
            "lines": [
                {
                    "product_supplier_id": 999,
                    "sale_quantity": 1,
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_sale_over_stock_conflict(
    client,
    auth_headers,
    workspace,
    product_supplier_link,
) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/sales",
        headers=auth_headers,
        json={
            "note": "too much",
            "lines": [
                {
                    "product_supplier_id": product_supplier_link["id"],
                    "sale_quantity": product_supplier_link["quantity"] + 1,
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize(
    "sale_data",
    [
        {
            "note": "empty lines",
            "lines": [],
        },
        {
            "note": "bad quantity",
            "lines": [
                {
                    "product_supplier_id": 1,
                    "sale_quantity": 0,
                }
            ],
        },
        {
            "note": "duplicate lines",
            "lines": [
                {
                    "product_supplier_id": 1,
                    "sale_quantity": 1,
                },
                {
                    "product_supplier_id": 1,
                    "sale_quantity": 2,
                },
            ],
        },
    ],
)
def test_add_sale_rejects_invalid_body(
    client,
    auth_headers,
    workspace,
    product_supplier_link,
    sale_data,
) -> None:
    for line in sale_data["lines"]:
        line["product_supplier_id"] = product_supplier_link["id"]

    response = client.post(
        f"/workspaces/{workspace['id']}/sales",
        headers=auth_headers,
        json=sale_data,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
