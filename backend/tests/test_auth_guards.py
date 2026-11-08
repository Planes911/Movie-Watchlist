"""Auth guard: every private route must reject requests without a valid token."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import get_settings

PROTECTED = [
    ("GET", "/api/watchlist"),
    ("POST", "/api/watchlist"),
    ("DELETE", "/api/watchlist/1"),
    ("GET", "/api/watched"),
    ("POST", "/api/watched"),
]
BODY = {"movieId": 1, "rating": 5, "review": "bagus"}


def _token(sub="1", exp_delta=timedelta(hours=1), secret=None, algorithm="HS256"):
    s = get_settings()
    payload = {"sub": sub, "exp": datetime.now(timezone.utc) + exp_delta}
    return jwt.encode(payload, secret if secret is not None else s.jwt_secret, algorithm=algorithm)


@pytest.mark.parametrize("method,path", PROTECTED)
def test_no_token_is_401(client, method, path):
    r = client.request(method, path, json=BODY)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("method,path", PROTECTED)
def test_garbage_token_is_401(client, method, path):
    r = client.request(method, path, json=BODY, headers={"Authorization": "Bearer ini.bukan.jwt"})
    assert r.status_code == 401


def test_wrong_auth_scheme_is_401(client):
    assert client.get("/api/watchlist", headers={"Authorization": "Basic abc123"}).status_code == 401


def test_expired_token_is_401(client, user_a):
    r = client.get("/api/watchlist", headers={"Authorization": f"Bearer {_token(exp_delta=timedelta(hours=-1))}"})
    assert r.status_code == 401
    assert "kedaluwarsa" in r.json()["message"]


def test_token_signed_with_other_secret_is_401(client, user_a):
    forged = _token(secret="secret-milik-penyerang-yang-panjang-sekali")
    assert client.get("/api/watchlist", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_alg_none_token_is_rejected(client, user_a):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, None, algorithm="none"
    )
    assert client.get("/api/watchlist", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_valid_token_for_deleted_user_is_401(client):
    ghost = _token(sub="99999")
    assert client.get("/api/watchlist", headers={"Authorization": f"Bearer {ghost}"}).status_code == 401


def test_valid_token_is_accepted(client, user_a):
    assert client.get("/api/watchlist", headers=user_a).status_code == 200
