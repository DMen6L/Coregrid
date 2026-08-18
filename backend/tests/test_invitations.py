from fastapi import status


def test_add_invitation(
    client,
    auth_headers,
    workspace,
    registered_second_user,
) -> None:
    payload = {
        "email": registered_second_user["email"],
        "role": "viewer",
    }
    response = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"]
    assert data["workspace_id"] == workspace["id"]
    assert data["email"] == payload["email"]
    assert data["role"] == payload["role"]
    assert data["accepted_at"] is None
    assert data["revoked_at"] is None
    assert "token_hash" not in data


def test_add_invitation_duplicate_active_conflict(
    client,
    auth_headers,
    workspace,
    invitation,
    registered_second_user,
) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        headers=auth_headers,
        json={
            "email": registered_second_user["email"],
            "role": "viewer",
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_add_invitation_existing_member_conflict(
    client,
    auth_headers,
    workspace,
    accepted_member,
    registered_second_user,
) -> None:
    response = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        headers=auth_headers,
        json={
            "email": registered_second_user["email"],
            "role": "viewer",
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_get_invitations(client, auth_headers, workspace, invitation) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/invitations",
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
    assert item["id"] == invitation["id"]
    assert item["workspace_id"] == workspace["id"]
    assert item["email"] == invitation["email"]
    assert item["role"] == invitation["role"]
    assert "token_hash" not in item


def test_get_invitations_search(
    client,
    auth_headers,
    workspace,
    invitation,
    registered_second_user,
) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/invitations",
        headers=auth_headers,
        params={"search": registered_second_user["email"]},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == invitation["id"]


def test_delete_invitation(client, auth_headers, workspace, invitation) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/invitations/{invitation['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(
        f"/workspaces/{workspace['id']}/invitations",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    item = response.json()["items"][0]
    assert item["id"] == invitation["id"]
    assert item["revoked_at"] is not None


def test_delete_invitation_revoked_noop(
    client,
    auth_headers,
    workspace,
    invitation,
) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/invitations/{invitation['id']}",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.delete(
        f"/workspaces/{workspace['id']}/invitations/{invitation['id']}",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_invitation_accepted_conflict(
    client,
    auth_headers,
    second_auth_headers,
    workspace,
    invitation,
) -> None:
    response = client.post(
        f"/me/accept/{invitation['id']}",
        headers=second_auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.delete(
        f"/workspaces/{workspace['id']}/invitations/{invitation['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_delete_invitation_not_found_error(client, auth_headers, workspace) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/invitations/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
