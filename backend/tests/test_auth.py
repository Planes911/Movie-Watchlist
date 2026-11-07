import jwt
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import User

VALID = {"username": "alice", "email": "alice@example.com", "password": "password123"}


def test_register_success_and_password_is_hashed(client):
    r = client.post("/api/auth/register", json=VALID)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert "password" not in body and "password_hash" not in body

    with SessionLocal() as db:
        user = db.scalars(select(User)).one()
    assert user.password_hash != VALID["password"]
    assert user.password_hash.startswith("$2")  # format bcrypt


def test_register_duplicate_email_is_409_case_insensitive(client):
    assert client.post("/api/auth/register", json=VALID).status_code == 201
    r = client.post("/api/auth/register", json={**VALID, "email": "ALICE@example.com"})
    assert r.status_code == 409
    assert "message" in r.json()


def test_register_validation_errors_are_400(client):
    assert client.post("/api/auth/register", json={**VALID, "password": "short"}).status_code == 400
    assert client.post("/api/auth/register", json={**VALID, "email": "bukan-email"}).status_code == 400
    r = client.post("/api/auth/register", json={"email": "x@example.com"})
    assert r.status_code == 400
    assert r.json()["error"] == "Bad Request"


def test_login_success_returns_token_and_user(client):
    client.post("/api/auth/register", json=VALID)
    r = client.post("/api/auth/login", json={"email": VALID["email"], "password": VALID["password"]})
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["email"] == VALID["email"]
    s = get_settings()
    payload = jwt.decode(data["token"], s.jwt_secret, algorithms=[s.jwt_algorithm])
    assert payload["sub"] == str(data["user"]["id"])


def test_login_failures_are_401_with_identical_message(client):
    client.post("/api/auth/register", json=VALID)
    wrong_pw = client.post("/api/auth/login", json={"email": VALID["email"], "password": "salah-banget"})
    no_user = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "password123"})
    assert wrong_pw.status_code == 401 and no_user.status_code == 401
    assert wrong_pw.json()["message"] == no_user.json()["message"]  # tidak membocorkan email terdaftar
