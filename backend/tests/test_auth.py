from fastapi import status
import pytest


def test_add_user(client, demo_user_data) -> None:
    response = client.post("/auth/register", json=demo_user_data)

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["name"] == demo_user_data["name"]
    assert data["email"] == demo_user_data["email"]
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.parametrize(
    "user_data",
    [
        {
            "name": "",
            "email": "some@email.com",
            "password": "DetailedPassword102",
        },
        {
            "name": "Some name",
            "email": "some email",
            "password": "DetailedPassword102",
        },
        {
            "name": "Some name",
            "email": "some@email.com",
            "password": "somePassword102",
        },
    ],
)
def test_rejects_wrong_registration_arguments(client, user_data) -> None:
    response = client.post("/auth/register", json=user_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_user_login(client, registered_user) -> None:
    demo_user_login = {
        "email": registered_user["email"],
        "password": registered_user["password"],
    }

    response = client.post("/auth/login", json=demo_user_login)

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"


@pytest.mark.parametrize(
    "user_data",
    [
        {
            "email": "unexsiting@email.com",
            "password": "randomPassword120",
        }
    ],
)
def test_wrong_or_unauthorized_login_credentials(
    client, registered_user, user_data
) -> None:
    response = client.post("/auth/login", json=user_data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = client.post(
        "/auth/login",
        json={"email": registered_user["email"], "password": "SomeotherPaassword"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_auth_me(client, registered_user, auth_headers) -> None:
    response = client.get("/auth/me", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == registered_user["email"]
    assert data["name"] == registered_user["name"]


def test_get_auth_me_requires_token(client) -> None:
    response = client.get("/auth/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
