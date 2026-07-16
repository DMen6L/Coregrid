from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_summaries():
    response = client.get("/summaries")

    assert response.status_code == 200
    print(response.json())


def test_get_products():
    response = client.get("/products")

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert "total" in data
    assert "total_pages" in data
    assert "has_next" in data
    assert "has_previous" in data

    assert isinstance(data["items"], list)
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= len(data["items"])
    assert data["has_previous"] is False
