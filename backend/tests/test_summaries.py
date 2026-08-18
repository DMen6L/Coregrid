from fastapi import status


def test_get_summaries(client, auth_headers, workspace, sale) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/summaries",
        headers=auth_headers,
        params={
            "days": 7,
            "best_sales_mode": "quantity",
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["dashboard_sales_value"] == 260
    assert data["dashboard_sales_count"] == 1
    assert data["low_stock"] == 1
    assert data["out_of_stock"] == 0

    assert len(data["latest_sales"]) == 1
    assert data["latest_sales"][0]["sales_value"] == 260

    assert len(data["top_products"]) == 1
    assert data["top_products"][0]["product_name"] == "linked_product"
    assert data["top_products"][0]["metric"] == 2

    assert len(data["top_suppliers"]) == 1
    assert data["top_suppliers"][0]["supplier_name"] == "new_supplier"
    assert data["top_suppliers"][0]["supplied_products"] == 1


def test_get_summaries_rejects_invalid_query(client, auth_headers, workspace) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/summaries",
        headers=auth_headers,
        params={
            "days": 1,
            "best_sales_mode": "quantity",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
