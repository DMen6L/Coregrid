from fastapi import status
import pytest


def test_get_me(client, auth_headers, registered_user, workspace) -> None:
    response = client.get(
        "/me",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["user"]["name"] == registered_user["name"]
    assert data["user"]["email"] == registered_user["email"]
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["id"] == workspace["id"]
    assert data["workspaces"][0]["role"] == "owner"
    assert data["invitations"] == []


def test_get_me_includes_pending_invitations(
    client,
    second_auth_headers,
    registered_second_user,
    workspace,
    invitation,
) -> None:
    response = client.get(
        "/me",
        headers=second_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["user"]["email"] == registered_second_user["email"]
    assert data["workspaces"] == []
    assert len(data["invitations"]) == 1
    assert data["invitations"][0]["id"] == invitation["id"]
    assert data["invitations"][0]["workspace_id"] == workspace["id"]
    assert data["invitations"][0]["role"] == invitation["role"]


@pytest.mark.parametrize(
    "param_name, value",
    [
        ("name", "Patched User"),
        ("email", "patched@email.com"),
    ],
)
def test_patch_me(client, auth_headers, workspace, param_name, value) -> None:
    response = client.patch(
        "/me",
        headers=auth_headers,
        json={
            param_name: value,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["user"][param_name] == value
    assert data["workspaces"][0]["id"] == workspace["id"]


def test_patch_me_duplicate_email_conflict(
    client,
    auth_headers,
    registered_second_user,
) -> None:
    response = client.patch(
        "/me",
        headers=auth_headers,
        json={"email": registered_second_user["email"]},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize(
    "update_violation_body",
    [
        {},
        {"name": ""},
        {"email": "bad email"},
    ],
)
def test_patch_me_rejects_invalid_body(
    client,
    auth_headers,
    update_violation_body,
) -> None:
    response = client.patch(
        "/me",
        headers=auth_headers,
        json=update_violation_body,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_patch_password(client, auth_headers, registered_user, workspace) -> None:
    response = client.patch(
        "/me/password",
        headers=auth_headers,
        json={
            "current_password": registered_user["password"],
            "new_password": "UpdatedStrong102",
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["user"]["email"] == registered_user["email"]
    assert data["workspaces"][0]["id"] == workspace["id"]


def test_patch_password_wrong_current_password(
    client,
    auth_headers,
    registered_user,
) -> None:
    response = client.patch(
        "/me/password",
        headers=auth_headers,
        json={
            "current_password": "WrongPassword102",
            "new_password": "UpdatedStrong102",
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_patch_password_rejects_repeated_password(
    client,
    auth_headers,
    registered_user,
) -> None:
    response = client.patch(
        "/me/password",
        headers=auth_headers,
        json={
            "current_password": registered_user["password"],
            "new_password": registered_user["password"],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_accept_invitation(
    client,
    second_auth_headers,
    workspace,
    invitation,
) -> None:
    response = client.post(
        f"/me/accept/{invitation['id']}",
        headers=second_auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == workspace["id"]
    assert data["name"] == workspace["name"]
    assert data["role"] == invitation["role"]


def test_accept_invitation_wrong_email_not_found(
    client,
    auth_headers,
    invitation,
) -> None:
    response = client.post(
        f"/me/accept/{invitation['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_leave_workspace(
    client,
    second_auth_headers,
    workspace,
    accepted_member,
) -> None:
    response = client.delete(
        f"/me/workspaces/{workspace['id']}",
        headers=second_auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_leave_workspace_owner_conflict(client, auth_headers, workspace) -> None:
    response = client.delete(
        f"/me/workspaces/{workspace['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_leave_workspace_not_found_error(client, auth_headers) -> None:
    response = client.delete(
        "/me/workspaces/999",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
