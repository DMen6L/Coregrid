from fastapi import status
import pytest


@pytest.mark.parametrize(
    "supplier_data",
    [
        {
            "name": "new_supplier",
            "phone_number": "+77070707070",
        },
    ],
)
def test_add_supplier(client, auth_headers, workspace, supplier_data) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/suppliers",
        headers=auth_headers,
        json=supplier_data,
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"]
    assert data["name"] == supplier_data["name"]
    assert data["phone_number"] == supplier_data["phone_number"]
    assert data["product_links"] == []


@pytest.mark.parametrize(
    "supplier_data",
    [
        {
            "name": "new_supplier",
            "phone_number": "+77080808080",
        },
        {
            "name": "test_supplier",
            "phone_number": "+77070707070",
        },
    ],
)
def test_add_supplier_uq_violation(
    client,
    auth_headers,
    workspace,
    supplier_data,
    supplier,
) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/suppliers",
        headers=auth_headers,
        json=supplier_data,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_get_suppliers(client, auth_headers, workspace, supplier) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/suppliers",
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
    assert item["id"] == supplier["id"]
    assert item["name"] == supplier["name"]
    assert item["phone_number"] == supplier["phone_number"]
    assert item["product_links_count"] == 0


def test_get_suppliers_search(client, auth_headers, workspace, supplier) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/suppliers",
        headers=auth_headers,
        params={"search": "new_sup"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == supplier["id"]


def test_get_supplier_by_id(client, auth_headers, workspace, supplier) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/suppliers/{supplier['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == supplier["id"]
    assert data["name"] == supplier["name"]
    assert data["phone_number"] == supplier["phone_number"]
    assert data["product_links"] == []


def test_get_supplier_by_id_not_found_error(
    client,
    auth_headers,
    workspace,
    supplier,
) -> None:
    not_found_id = supplier["id"] + 999
    response = client.get(
        f"/workspaces/{workspace['id']}/suppliers/{not_found_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "param_name, value",
    [
        ("name", "patched_supplier_name"),
        ("phone_number", "+77080808080"),
    ],
)
def test_patch_supplier(
    client,
    auth_headers,
    workspace,
    supplier,
    param_name,
    value,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/suppliers/{supplier['id']}",
        headers=auth_headers,
        json={
            param_name: value,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data[param_name] == value


@pytest.mark.parametrize(
    "param_name, value",
    [
        ("name", "new_supplier"),
        ("phone_number", "+77070707070"),
    ],
)
def test_patch_supplier_uq_violation(
    client,
    auth_headers,
    workspace,
    supplier,
    param_name,
    value,
) -> None:
    payload = {
        "name": "test_violation_supplier",
        "phone_number": "+77080808080",
    }

    post_response = client.post(
        f"/workspaces/{workspace['id']}/suppliers",
        headers=auth_headers,
        json=payload,
    )

    assert post_response.status_code == status.HTTP_201_CREATED

    violation_supplier = post_response.json()

    response = client.patch(
        f"/workspaces/{workspace['id']}/suppliers/{violation_supplier['id']}",
        headers=auth_headers,
        json={
            param_name: value,
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize(
    "update_violation_body",
    [
        {},
        {
            "name": "",
        },
        {"phone_number": ""},
    ],
)
def test_patch_supplier_rejects_invalid_body(
    client,
    auth_headers,
    workspace,
    supplier,
    update_violation_body,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/suppliers/{supplier['id']}",
        headers=auth_headers,
        json=update_violation_body,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
