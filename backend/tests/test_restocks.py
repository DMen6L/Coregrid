from fastapi import status
import pytest


def test_add_restock(
    client,
    auth_headers,
    workspace,
    product_supplier_link,
) -> None:
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
    assert line["restock_quantity"] == 3
    assert line["unit_cost_snapshot"] == 90
    assert line["quantity_unit_snapshot"] == "шт"


def test_get_restocks(client, auth_headers, workspace, restock) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/restocks",
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
    assert item["id"] == restock["id"]
    assert item["note"] == restock["note"]
    assert item["costs"] == 270
    assert item["lines_count"] == 1


def test_get_restock_by_id(client, auth_headers, workspace, restock) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/restocks/{restock['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == restock["id"]
    assert data["note"] == restock["note"]
    assert len(data["lines"]) == 1


def test_get_restock_by_id_not_found_error(
    client,
    auth_headers,
    workspace,
    restock,
) -> None:
    not_found_id = restock["id"] + 999
    response = client.get(
        f"/workspaces/{workspace['id']}/restocks/{not_found_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_restock_missing_product_supplier_error(
    client,
    auth_headers,
    workspace,
) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/restocks",
        headers=auth_headers,
        json={
            "note": "missing link",
            "lines": [
                {
                    "product_supplier_id": 999,
                    "restock_quantity": 3,
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "restock_data",
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
                    "restock_quantity": 0,
                }
            ],
        },
        {
            "note": "duplicate lines",
            "lines": [
                {
                    "product_supplier_id": 1,
                    "restock_quantity": 1,
                },
                {
                    "product_supplier_id": 1,
                    "restock_quantity": 2,
                },
            ],
        },
    ],
)
def test_add_restock_rejects_invalid_body(
    client,
    auth_headers,
    workspace,
    product_supplier_link,
    restock_data,
) -> None:
    for line in restock_data["lines"]:
        line["product_supplier_id"] = product_supplier_link["id"]

    response = client.post(
        f"/workspaces/{workspace['id']}/restocks",
        headers=auth_headers,
        json=restock_data,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
