from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import WorkspaceMembership


TEST_PASSWORD = "Str0ngPass!234"


def unique_suffix() -> str:
    return uuid4().hex[:10]


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{unique_suffix()}@example.com"


def unique_phone_number() -> str:
    return f"+7{uuid4().int % 10_000_000_000:010d}"


def unique_iin() -> str:
    return f"{uuid4().int % 1_000_000_000_000:012d}"


def register_user(
    client: TestClient,
    *,
    email: str | None = None,
    name: str | None = None,
    password: str = TEST_PASSWORD,
) -> dict:
    user_email = email or unique_email()
    response = client.post(
        "/auth/register",
        json={
            "email": user_email,
            "name": name or f"Test User {unique_suffix()}",
            "password": password,
        },
    )

    assert response.status_code == 201, response.json()
    return response.json()


def login_headers(
    client: TestClient,
    email: str,
    *,
    password: str = TEST_PASSWORD,
) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.json()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_workspace(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str | None = None,
) -> dict:
    response = client.post(
        "/workspaces",
        headers=headers,
        json={"name": name or f"Workspace {unique_suffix()}"},
    )

    assert response.status_code == 201, response.json()
    return response.json()


def create_workspace_context(
    client: TestClient,
    *,
    user_prefix: str = "owner",
    workspace_name: str | None = None,
) -> dict:
    user = register_user(
        client,
        email=unique_email(user_prefix),
        name=f"{user_prefix.title()} User",
    )
    headers = login_headers(client, user["email"])
    workspace = create_workspace(client, headers, name=workspace_name)

    return {
        "user": user,
        "headers": headers,
        "workspace": workspace,
        "workspace_id": workspace["id"],
    }


def add_workspace_membership(
    db_session: Session,
    *,
    user_id: int,
    workspace_id: int,
    role: str,
) -> WorkspaceMembership:
    membership = WorkspaceMembership(
        user_id=user_id,
        workspace_id=workspace_id,
        role=role,
    )

    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)

    return membership


def assert_paginated_response(data: dict) -> None:
    assert set(data) == {
        "items",
        "page",
        "page_size",
        "total",
        "total_pages",
        "has_next",
        "has_previous",
    }
    assert isinstance(data["items"], list)
    assert isinstance(data["page"], int)
    assert isinstance(data["page_size"], int)
    assert isinstance(data["total"], int)
    assert isinstance(data["total_pages"], int)
    assert isinstance(data["has_next"], bool)
    assert isinstance(data["has_previous"], bool)
