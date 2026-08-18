from fastapi import status
import pytest


@pytest.mark.parametrize(
    "company_data",
    [
        {
            "name": "new_company",
            "iin": "070707070707",
        },
    ],
)
def test_add_company(client, auth_headers, workspace, company_data) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/companies",
        headers=auth_headers,
        json=company_data,
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"]
    assert data["name"] == company_data["name"]
    assert data["iin"] == company_data["iin"]


@pytest.mark.parametrize(
    "company_data",
    [
        {
            "name": "new_company",
            "iin": "080808080808",
        },
        {
            "name": "test_company",
            "iin": "070707070707",
        },
    ],
)
def test_add_company_uq_violation(
    client,
    auth_headers,
    workspace,
    company_data,
    company,
) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/companies",
        headers=auth_headers,
        json=company_data,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_get_companies(client, auth_headers, workspace, company) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/companies",
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

    assert item["id"] == company["id"]
    assert item["name"] == company["name"]
    assert item["iin"] == company["iin"]


def test_get_company_by_id(client, auth_headers, workspace, company) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/companies/{company['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == company["id"]
    assert data["name"] == company["name"]
    assert data["iin"] == company["iin"]


def test_get_company_by_id_not_found_error(
    client, auth_headers, workspace, company
) -> None:
    not_found_id = company["id"] + 999
    response = client.get(
        f"/workspaces/{workspace['id']}/companies/{not_found_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "param_name, value",
    [
        ("name", "patched_company_name"),
        ("iin", "080808080808"),
    ],
)
def test_patch_company(
    client,
    auth_headers,
    workspace,
    company,
    param_name,
    value,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/companies/{company['id']}",
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
        ("name", "new_company"),
        ("iin", "070707070707"),
    ],
)
def test_patch_company_uq_violation(
    client,
    auth_headers,
    workspace,
    company,
    param_name,
    value,
) -> None:
    payload = {
        "name": "test_violation_company",
        "iin": "080808080808",
    }

    post_response = client.post(
        f"/workspaces/{workspace['id']}/companies",
        headers=auth_headers,
        json=payload,
    )

    assert post_response.status_code == status.HTTP_201_CREATED

    violation_company = post_response.json()

    response = client.patch(
        f"/workspaces/{workspace['id']}/companies/{violation_company['id']}",
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
        {"iin": ""},
    ],
)
def test_patch_company_rejects_invalid_body(
    client,
    auth_headers,
    workspace,
    company,
    update_violation_body,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/companies/{company['id']}",
        headers=auth_headers,
        json=update_violation_body,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_patch_company_iin_to_null(
    client,
    auth_headers,
    workspace,
    company,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/companies/{company['id']}",
        headers=auth_headers,
        json={"iin": None},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["iin"] is None
