from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_summaries():
    response = client.get("/summaries")

    assert response.status_code == 200
    data = response.json()

    assert data == {
        "dashboard_sales_value": 0,
        "dashboard_sales_count": 0,
        "low_stock": 0,
        "out_of_stock": 0,
        "latest_sales": [],
        "top_products": [],
        "top_suppliers": [],
    }
