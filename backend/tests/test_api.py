from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_summaries():
    response = client.get("/summaries")

    assert response.status_code == 200
    print(response.json())
