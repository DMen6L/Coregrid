from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def debug_response(response):
    print("RESPONSE:\n")
    print(f"STATUS: {response.status_code}\n")
    print(f"BODY: {response.text}\n")


# TEST DATA FOR TESTING THE ENDPOINTS
company_test_data = [
    {"iin": "121212121212", "name": "string1"},
    {"iin": "131313131313", "name": "string2"},
]


def test_root():
    response = client.get("/")

    debug_response(response)
    assert response.status_code == 200


# =====================
# COMPANIES TABLE TESTS
# =====================


def test_companies_post():
    for payload in company_test_data:
        print(f"PAYLOAD: {payload}\n")

        response = client.post("/companies", json=payload)
        debug_response(response)
        assert response.status_code == 201


def test_companies_patch():
    company_test_data[0]["name"] = "new_name1"
    payload = {"name": company_test_data[0]["name"]}

    print(f"PAYLOAD: {payload}\n")

    response = client.patch("/companies/1", json=payload)
    debug_response(response)

    assert response.status_code == 200


def test_companies_get_all():
    response = client.get("/companies")
    debug_response(response)

    assert response.status_code == 200


def test_companies_get_one():
    response = client.get("/companies/1")
    debug_response(response)

    assert response.status_code == 200


def test_delete_all():
    response = client.delete("/cleanup")
    debug_response(response)

    assert response.status_code == 204
