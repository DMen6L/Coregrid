from fastapi import status
import pytest


@pytest.mark.parametrize(
    "workspace_data",
    [
        {
            "name": "new_workspace",
        }
    ],
)
def test_add_workspace(client, auth_headers, workspace_data) -> None:
    response = client.post(
        "/workspaces",
        headers=auth_headers,
        json=workspace_data,
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["id"] is not None
    assert data["name"] == workspace_data["name"]
    assert data["role"] == "owner"


def test_get_workspace(client, auth_headers, workspace) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == workspace["id"]
    assert data["name"] == workspace["name"]
    assert data["role"] == "owner"


def test_get_workspace_logs(client, auth_headers, workspace) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/logs",
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

    log = data["items"][0]
    assert log["workspace_id"] == workspace["id"]
    assert log["action"] == "workspace.created"
    assert log["entity_type"] == "workspace"
    assert log["entity_id"] == str(workspace["id"])
    assert log["entity_label"] == workspace["name"]
    assert log["changes"] is None
    assert log["extra_data"]["owner_email"] is not None
