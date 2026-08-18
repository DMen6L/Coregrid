from fastapi import status


def test_get_tags(client, auth_headers, workspace, product) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/tags",
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

    tag_names = sorted(item["name"] for item in data["items"])
    assert tag_names == ["second tag", "test tag"]

    for item in data["items"]:
        assert item["id"]
        assert item["usage_count"] == 1


def test_get_tags_search(client, auth_headers, workspace, product) -> None:
    response = client.get(
        f"/workspaces/{workspace['id']}/tags",
        headers=auth_headers,
        params={"search": "test"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "test tag"


def test_delete_tag(client, auth_headers, workspace, product) -> None:
    tags_response = client.get(
        f"/workspaces/{workspace['id']}/tags",
        headers=auth_headers,
        params={"search": "test"},
    )
    assert tags_response.status_code == status.HTTP_200_OK

    tag = tags_response.json()["items"][0]

    response = client.delete(
        f"/workspaces/{workspace['id']}/tags/{tag['id']}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_tag_not_found_error(client, auth_headers, workspace, product) -> None:
    response = client.delete(
        f"/workspaces/{workspace['id']}/tags/999",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
