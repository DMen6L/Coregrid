from fastapi import status


def test_health(client) -> None:
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "ok"


def test_ready(client) -> None:
    response = client.get("/ready")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "ok"
