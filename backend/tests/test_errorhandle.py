import pytest
from fastapi.testclient import TestClient
from app import db as db_module
from app.main import app
from app import main

@pytest.fixture(scope="session")
def test_client(tmp_path_factory):
    test_db_path = tmp_path_factory.mktemp("data") / "delivery_test.db"
    db_module.DB_PATH = test_db_path

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

@pytest.fixture(autouse=True)
def cleanup_db(test_client):
    yield
    with db_module.get_db() as conn:
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM order_items")

def test_register_duplicate_email_returns_conflict(test_client):
    payload = {"name": "Alice", "email": "alice@test.com", "password": "secret123!"}

    first_response = test_client.post("/api/auth/register", json=payload)
    assert first_response.status_code == 200

    second_response = test_client.post("/api/auth/register", json=payload)
    assert second_response.status_code == 409

    body = second_response.json()
    assert body["error"]["code"] == "USER_EXISTS"
    assert "already registered" in body["error"]["message"].lower()

def test_email_is_incorrect(test_client):
    payload = {"name": "Alice", "email": "alice.test.com", "password": "secret123!"}
    first_response = test_client.post("/api/auth/register", json=payload)
    assert first_response.status_code == 422

    body = first_response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "email" in body["error"]["message"].lower()

def test_password_is_incorrect(test_client):
    payload = {"name": "Alice", "email": "alice@test.com", "password": "secre"}
    first_response = test_client.post("/api/auth/register", json=payload)
    assert first_response.status_code == 422

    body = first_response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "8 characters" in body["error"]["message"].lower()

def test_multiple_validation_errors_reported_together(test_client):
    payload = {"name": "Alice", "email": "alice.test.com", "password": "secret123"}
    first_response = test_client.post("/api/auth/register", json=payload)
    assert first_response.status_code == 422

    body = first_response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    details = body["error"]["details"]
    assert "email" in details
    assert "password" in details

def test_database_connect_error(monkeypatch, test_client):
    monkeypatch.setattr(db_module, "DB_PATH", "tmp233/test.db")
    payload = {"name": "Alice", "email": "alice@test.com", "password": "secret123!"}
    first_response = test_client.post("/api/auth/register", json=payload)

    assert first_response.status_code == 500

    body = first_response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "Something went wrong, please try again later."

def test_login_with_wrong_password_returns_invalid_credentials(test_client):
    register_payload = {"name": "Alice", "email": "alice@test.com", "password": "secret123!"}
    test_client.post("/api/auth/register", json=register_payload)

    login_payload = {"email": "alice@test.com", "password": "wrongpassword"}
    response = test_client.post("/api/auth/login", json=login_payload)

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_LOGIN"
    assert "invalid" in body["error"]["message"].lower()


def test_login_with_nonexistent_email_returns_invalid_credentials(test_client):
    login_payload = {"email": "nobody@test.com", "password": "whatever123!"}
    response = test_client.post("/api/auth/login", json=login_payload)

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_LOGIN"

# test get_current_user,api->"/api/auth/users/me"
# token没问题，但用户在数据库被删除
def test_get_current_user_returns_invalid_credentials_when_user_deleted(test_client):
    register_payload = {"name": "Carol", "email": "carol@test.com", "password": "secret123!"}
    register_response = test_client.post("/api/auth/register", json=register_payload)
    token = register_response.json()["token"]

    with db_module.get_db() as conn:
        conn.execute("DELETE FROM users WHERE email = ?", ("carol@test.com",))

    response = test_client.get(
        "/api/auth/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"

def test_recommendations_returns_external_service_error_when_llm_fails(test_client, monkeypatch):
    def fake_parse(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr(main.client.chat.completions, "parse", fake_parse)

    response = test_client.post("/api/recommendations", json={"user_input": "pizza"})

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "EXTERNAL_SERVICE_ERROR"

def test_get_store_returns_not_found_for_nonexistent_store(test_client):
    response = test_client.get("/api/stores/99999")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "STORE_NOT_FOUND"


def test_create_order_returns_not_found_when_food_item_missing(test_client):
    register_payload = {"name": "Dan", "email": "dan@test.com", "password": "secret123!"}
    register_response = test_client.post("/api/auth/register", json=register_payload)
    token = register_response.json()["token"]

    order_payload = {"items": [{"food_id": 99999, "quantity": 1}]}
    response = test_client.post(
        "/api/orders",
        json=order_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "FOOD_UNAVAILABLE"