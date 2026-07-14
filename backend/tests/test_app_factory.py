from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_system_and_static_routes_are_registered():
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/metrics").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/dashboard").status_code == 200


def test_login_contract_is_preserved(monkeypatch):
    monkeypatch.setattr(
        "backend.api.auth_routes.authenticate_user",
        lambda username, password: {
            "id": "user-1",
            "username": username,
            "email": "user@example.com",
            "full_name": "Test User",
        },
    )
    response = client.post("/api/auth/login", json={"username": "user", "password": "secret"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user_id"] == "user-1"
    assert payload["username"] == "user"
    assert payload["message"] == "Login successful"
