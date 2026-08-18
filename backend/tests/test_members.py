from fastapi import status


def test_get_members(
    client,
    auth_headers,
    workspace,
    accepted_member,
    owner_member,
) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 2
    assert data["total_pages"] == 1
    assert data["has_next"] is False
    assert data["has_previous"] is False

    member_ids = {item["id"] for item in data["items"]}
    assert owner_member["id"] in member_ids
    assert accepted_member["id"] in member_ids


def test_get_members_search(
    client,
    auth_headers,
    workspace,
    accepted_member,
    registered_second_user,
) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=auth_headers,
        params={"search": registered_second_user["email"]},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == accepted_member["id"]


def test_get_member_by_id(client, auth_headers, workspace, accepted_member) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/members/{accepted_member['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == accepted_member["id"]
    assert data["name"] == accepted_member["name"]
    assert data["email"] == accepted_member["email"]
    assert data["role"] == accepted_member["role"]
    assert data["user_id"]


def test_get_member_by_id_not_found_error(
    client,
    auth_headers,
    workspace,
    accepted_member,
) -> None:
    not_found_id = accepted_member["id"] + 999
    response = client.get(
        f"/workspaces/{workspace['id']}/members/{not_found_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_patch_member_role(client, auth_headers, workspace, accepted_member) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/members/{accepted_member['id']}/role",
        headers=auth_headers,
        params={"new_role": "manager"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == accepted_member["id"]
    assert data["role"] == "manager"


def test_patch_member_role_same_role_error(
    client,
    auth_headers,
    workspace,
    accepted_member,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/members/{accepted_member['id']}/role",
        headers=auth_headers,
        params={"new_role": accepted_member["role"]},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_patch_member_role_self_forbidden(
    client,
    auth_headers,
    workspace,
    owner_member,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/members/{owner_member['id']}/role",
        headers=auth_headers,
        params={"new_role": "viewer"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_patch_member_role_rejects_owner_role(
    client,
    auth_headers,
    workspace,
    accepted_member,
) -> None:
    response = client.patch(
        f"/workspaces/{workspace['id']}/members/{accepted_member['id']}/role",
        headers=auth_headers,
        params={"new_role": "owner"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_delete_member(client, auth_headers, workspace, accepted_member) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/members/{accepted_member['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=auth_headers,
        params={"search": accepted_member["email"]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total"] == 0


def test_delete_member_self_forbidden(
    client,
    auth_headers,
    workspace,
    owner_member,
) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/members/{owner_member['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_member_not_found_error(client, auth_headers, workspace) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/members/999",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
