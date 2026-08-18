from fastapi import status
import pytest


@pytest.mark.parametrize(
    "product_data",
    [
        {
            "name": "new_product",
            "company_id": 1,
            "tags": ["test tag", "second tag"],
            "quantity_unit": "шт",
            "low_stock_threshold": 5,
        },
    ],
)
def test_add_product(
    client,
    auth_headers,
    workspace,
    company,
    product_data,
) -> None:
    product_data["company_id"] = company["id"]
    response = client.post(
        f"/workspaces/{workspace['id']}/products",
        headers=auth_headers,
        json=product_data,
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"]
    assert data["name"] == product_data["name"]
    assert data["company_id"] == company["id"]
    assert data["company_name"] == company["name"]
    assert data["quantity_unit"] == product_data["quantity_unit"]
    assert data["low_stock_threshold"] == product_data["low_stock_threshold"]
    assert sorted(tag["name"] for tag in data["tags"]) == sorted(product_data["tags"])
    assert data["supplier_links"] == []


def test_add_product_uq_violation(
    client,
    auth_headers,
    workspace,
    company,
    product,
) -> None:
    payload = {
        "name": product["name"],
        "company_id": company["id"],
        "tags": [],
        "quantity_unit": product["quantity_unit"],
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/products",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_get_products(client, auth_headers, workspace, product_with_link) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/products",
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
    assert item["id"] == product_with_link["id"]
    assert item["name"] == product_with_link["name"]
    assert item["company_name"] == product_with_link["company_name"]
    assert item["tags"] == ["linked tag"]
    assert item["suppliers_count"] == 1
    assert item["total_quantity"] == 7
    assert item["min_purchase_price"] == 100
    assert item["margin_percent"] == 20
    assert item["min_sale_price"] == 130
    assert item["stock_status"] == "available"


@pytest.mark.parametrize(
    "params",
    [
        {"search": "linked"},
        {"search": "linked tag"},
        {"company_name": "new_comp"},
        {"supplier_name": "new_sup"},
        {"tags": "linked tag"},
        {"stock_status": "available"},
    ],
)
def test_get_products_filters(
    client,
    auth_headers,
    workspace,
    product_with_link,
    params,
) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/products",
        headers=auth_headers,
        params=params,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == product_with_link["id"]


def test_get_products_stock_status_out(
    client,
    auth_headers,
    workspace,
    product,
) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/products",
        headers=auth_headers,
        params={"stock_status": "out"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == product["id"]
    assert data["items"][0]["stock_status"] == "out"


def test_get_product_by_id(
    client,
    auth_headers,
    workspace,
    product_with_link,
) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/products/{product_with_link['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == product_with_link["id"]
    assert data["name"] == product_with_link["name"]
    assert data["company_id"] == product_with_link["company_id"]
    assert len(data["supplier_links"]) == 1


def test_get_product_by_id_not_found_error(
    client,
    auth_headers,
    workspace,
    product,
) -> None:
    not_found_id = product["id"] + 999
    response = client.get(
        f"/workspaces/{workspace['id']}/products/{not_found_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "param_name, value",
    [
        ("name", "patched_product_name"),
        ("low_stock_threshold", 10),
        ("quantity_unit", "кг"),
    ],
)
def test_patch_product(
    client,
    auth_headers,
    workspace,
    product,
    param_name,
    value,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        headers=auth_headers,
        json={
            param_name: value,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data[param_name] == value


def test_patch_product_tags(client, auth_headers, workspace, product) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        headers=auth_headers,
        json={"tags": ["patched tag"]},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert [tag["name"] for tag in data["tags"]] == ["patched tag"]


def test_patch_product_uq_violation(
    client,
    auth_headers,
    workspace,
    company,
    product,
) -> None:
    payload = {
        "name": "violation_product",
        "company_id": company["id"],
        "tags": [],
        "quantity_unit": product["quantity_unit"],
    }
    post_response = client.post(
        f"/workspaces/{workspace['id']}/products",
        headers=auth_headers,
        json=payload,
    )

    assert post_response.status_code == status.HTTP_201_CREATED

    violation_product = post_response.json()

    response = client.patch(
        f"/workspaces/{workspace['id']}/products/{violation_product['id']}",
        headers=auth_headers,
        json={"name": product["name"]},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize(
    "update_violation_body",
    [
        {},
        {"name": ""},
        {"low_stock_threshold": -1},
    ],
)
def test_patch_product_rejects_invalid_body(
    client,
    auth_headers,
    workspace,
    product,
    update_violation_body,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product['id']}",
        headers=auth_headers,
        json=update_violation_body,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_add_product_atomic(
    client,
    auth_headers,
    workspace,
) -> None:
    payload = {
        "product_name": "atomic_product",
        "company": {
            "name": "atomic_company",
            "iin": "090909090909",
        },
        "tags": ["atomic tag"],
        "quantity_unit": "шт",
        "low_stock_threshold": 3,
        "product_links": [
            {
                "supplier": {
                    "name": "atomic_supplier",
                    "phone_number": "+77090909090",
                },
                "purchase_price": 100,
                "margin_percent": 25,
                "sale_price": 130,
                "quantity": 4,
            }
        ],
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/products/full",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"]
    assert data["name"] == payload["product_name"]
    assert data["company_name"] == payload["company"]["name"]
    assert [tag["name"] for tag in data["tags"]] == payload["tags"]
    assert len(data["supplier_links"]) == 1
    assert data["supplier_links"][0]["supplier_name"] == payload["product_links"][0][
        "supplier"
    ]["name"]


def test_patch_product_link(
    client,
    auth_headers,
    workspace,
    product_with_link,
    product_supplier_link,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product_with_link['id']}/links/{product_supplier_link['id']}",
        headers=auth_headers,
        json={"quantity": 3},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == product_supplier_link["id"]
    assert data["quantity"] == 3


def test_patch_product_link_floor_price_violation(
    client,
    auth_headers,
    workspace,
    product_with_link,
    product_supplier_link,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product_with_link['id']}/links/{product_supplier_link['id']}",
        headers=auth_headers,
        json={"sale_price": 100},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_patch_product_atomic(
    client,
    auth_headers,
    workspace,
    product_with_link,
    product_supplier_link,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/products/{product_with_link['id']}/full",
        headers=auth_headers,
        json={
            "name": "atomic_updated_product",
            "tags": ["updated tag"],
            "product_links": [
                {
                    "id": product_supplier_link["id"],
                    "quantity": 2,
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["name"] == "atomic_updated_product"
    assert [tag["name"] for tag in data["tags"]] == ["updated tag"]
    assert data["supplier_links"][0]["quantity"] == 2


def test_delete_product_link(
    client,
    auth_headers,
    workspace,
    empty_product_with_link,
    empty_product_supplier_link,
) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/products/{empty_product_with_link['id']}/links/{empty_product_supplier_link['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_product_link_with_stock_conflict(
    client,
    auth_headers,
    workspace,
    product_with_link,
    product_supplier_link,
) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/products/{product_with_link['id']}/links/{product_supplier_link['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
