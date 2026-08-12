from .helpers import (
    add_workspace_membership,
    create_workspace_context,
    login_headers,
    register_user,
    unique_email,
    unique_suffix,
)


def test_register_login_me_and_workspace_overview(client):
    email = unique_email("account")
    user = register_user(client, email=email, name="Account User")
    headers = login_headers(client, email)

    auth_me_response = client.get("/auth/me", headers=headers)
    assert auth_me_response.status_code == 200
    assert auth_me_response.json() == user

    empty_overview_response = client.get("/me", headers=headers)
    assert empty_overview_response.status_code == 200
    empty_overview = empty_overview_response.json()
    assert empty_overview["user"] == user
    assert empty_overview["workspaces"] == []
    assert empty_overview["invitations"] == []

    workspace_response = client.post(
        "/workspaces",
        headers=headers,
        json={"name": f"Account workspace {unique_suffix()}"},
    )
    assert workspace_response.status_code == 201

    overview_response = client.get("/me", headers=headers)
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["user"] == user
    assert overview["workspaces"] == [workspace_response.json()]
    assert overview["workspaces"][0]["role"] == "owner"


def test_patch_me_updates_profile_and_rejects_duplicate_email(client):
    first_user = register_user(
        client,
        email=unique_email("profile"),
        name="Profile User",
    )
    second_user = register_user(
        client,
        email=unique_email("duplicate"),
        name="Duplicate User",
    )
    headers = login_headers(client, first_user["email"])
    new_email = unique_email("updated")

    update_response = client.patch(
        "/me",
        headers=headers,
        json={
            "name": "Updated Profile User",
            "email": new_email.upper(),
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["user"]["id"] == first_user["id"]
    assert data["user"]["name"] == "Updated Profile User"
    assert data["user"]["email"] == new_email

    duplicate_response = client.patch(
        "/me",
        headers=headers,
        json={"email": second_user["email"]},
    )

    assert duplicate_response.status_code == 409
    assert (
        duplicate_response.json()["detail"]
        == "Violated unique constraint: uq_users_email"
    )


def test_workspace_invitations_and_member_admin_flow(client):
    owner_context = create_workspace_context(client, user_prefix="owner")
    workspace_id = owner_context["workspace_id"]
    invitee = register_user(
        client,
        email=unique_email("invitee"),
        name="Invited User",
    )

    invitation_response = client.post(
        f"/workspaces/{workspace_id}/invitations",
        headers=owner_context["headers"],
        json={
            "email": invitee["email"].upper(),
            "role": "viewer",
        },
    )

    assert invitation_response.status_code == 201
    invitation = invitation_response.json()
    assert invitation["email"] == invitee["email"]
    assert invitation["workspace_id"] == workspace_id
    assert invitation["role"] == "viewer"
    assert "token_hash" not in invitation

    duplicate_response = client.post(
        f"/workspaces/{workspace_id}/invitations",
        headers=owner_context["headers"],
        json={
            "email": invitee["email"],
            "role": "viewer",
        },
    )
    assert duplicate_response.status_code == 409

    invitee_headers = login_headers(client, invitee["email"])
    personal_overview_response = client.get("/me", headers=invitee_headers)
    assert personal_overview_response.status_code == 200
    personal_invitations = personal_overview_response.json()["invitations"]
    assert len(personal_invitations) == 1
    assert personal_invitations[0]["id"] == invitation["id"]
    assert (
        personal_invitations[0]["workspace_name"]
        == owner_context["workspace"]["name"]
    )

    accept_response = client.post(
        f"/me/invitations/accept/{invitation['id']}",
        headers=invitee_headers,
    )
    assert accept_response.status_code == 200
    assert accept_response.json() == {
        "id": workspace_id,
        "name": owner_context["workspace"]["name"],
        "role": "viewer",
    }

    members_response = client.get(
        f"/workspaces/{workspace_id}/members",
        headers=owner_context["headers"],
        params={"search": invitee["email"], "page_size": 10},
    )
    assert members_response.status_code == 200
    member_rows = members_response.json()["items"]
    assert len(member_rows) == 1
    member_summary = member_rows[0]
    assert member_summary["email"] == invitee["email"]
    assert member_summary["role"] == "viewer"

    detail_response = client.get(
        f"/workspaces/{workspace_id}/members/{member_summary['id']}",
        headers=owner_context["headers"],
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["user_id"] == invitee["id"]

    role_response = client.patch(
        f"/workspaces/{workspace_id}/members/{member_summary['id']}/role",
        headers=owner_context["headers"],
        params={"new_role": "operator"},
    )
    assert role_response.status_code == 200
    assert role_response.json()["role"] == "operator"

    delete_response = client.delete(
        f"/workspaces/{workspace_id}/members/{member_summary['id']}",
        headers=owner_context["headers"],
    )
    assert delete_response.status_code == 204

    deleted_detail_response = client.get(
        f"/workspaces/{workspace_id}/members/{member_summary['id']}",
        headers=owner_context["headers"],
    )
    assert deleted_detail_response.status_code == 404


def test_workspace_permissions_restrict_catalog_writes(client, db_session):
    owner_context = create_workspace_context(client, user_prefix="permissions-owner")
    workspace_id = owner_context["workspace_id"]
    viewer = register_user(
        client,
        email=unique_email("viewer"),
        name="Viewer User",
    )
    add_workspace_membership(
        db_session,
        user_id=viewer["id"],
        workspace_id=workspace_id,
        role="viewer",
    )
    viewer_headers = login_headers(client, viewer["email"])

    read_response = client.get(
        f"/workspaces/{workspace_id}/companies",
        headers=viewer_headers,
    )
    assert read_response.status_code == 200

    write_response = client.post(
        f"/workspaces/{workspace_id}/companies",
        headers=viewer_headers,
        json={"name": f"Forbidden company {unique_suffix()}"},
    )
    assert write_response.status_code == 403
    assert write_response.json()["detail"] == "Insufficient workspace permission"


def test_non_member_cannot_access_workspace(client):
    owner_context = create_workspace_context(client, user_prefix="owner")
    outsider = register_user(
        client,
        email=unique_email("outsider"),
        name="Outsider User",
    )
    outsider_headers = login_headers(client, outsider["email"])

    response = client.get(
        f"/workspaces/{owner_context['workspace_id']}/companies",
        headers=outsider_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "No access to this workspace"
