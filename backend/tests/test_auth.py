import uuid

from fastapi.testclient import TestClient

from app.database import crud
from app.database.session import SessionLocal
from app.main import app


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@test.afririsk"


def test_register_creates_admin_only_for_the_very_first_user():
    db = SessionLocal()
    try:
        already_bootstrapped = crud.count_users(db) > 0
    finally:
        db.close()

    email = _unique_email("bootstrap")
    with TestClient(app) as client:
        response = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == email
    assert data["access_token"]
    expected_role = "agent" if already_bootstrapped else "admin"
    assert data["user"]["role"] == expected_role


def test_register_rejects_duplicate_email():
    email = _unique_email("dup")
    with TestClient(app) as client:
        first = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
        assert first.status_code == 200
        second = client.post("/auth/register", json={"email": email, "password": "another-password"})
    assert second.status_code == 400


def test_login_succeeds_with_correct_credentials_and_fails_otherwise():
    email = _unique_email("login")
    with TestClient(app) as client:
        client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})

        ok = client.post("/auth/login", json={"email": email, "password": "correct-horse-1"})
        assert ok.status_code == 200
        assert ok.json()["access_token"]

        wrong = client.post("/auth/login", json={"email": email, "password": "wrong-password"})
        assert wrong.status_code == 401

        unknown = client.post("/auth/login", json={"email": _unique_email("nobody"), "password": "whatever1"})
        assert unknown.status_code == 401


def test_me_requires_a_valid_token():
    email = _unique_email("me")
    with TestClient(app) as client:
        register = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
        token = register.json()["access_token"]

        authenticated = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert authenticated.status_code == 200
        assert authenticated.json()["email"] == email

        anonymous = client.get("/auth/me")
        assert anonymous.status_code == 401

        garbage = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
        assert garbage.status_code == 401


def test_only_admin_can_create_users_with_a_chosen_role(agent_headers, admin_headers):
    payload = {"email": _unique_email("created"), "password": "correct-horse-1", "role": "viewer"}
    with TestClient(app) as client:
        forbidden = client.post("/auth/users", json=payload, headers=agent_headers)
        assert forbidden.status_code == 403

        allowed = client.post("/auth/users", json=payload, headers=admin_headers)
        assert allowed.status_code == 200
        assert allowed.json()["role"] == "viewer"
