"""Fixture bersama. Test memakai SQLite in-memory + Gemini palsu: cepat, tanpa internet & tanpa kuota."""
import os

# HARUS di-set sebelum modul app diimpor (config dibaca saat import).
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["GEMINI_API_KEY"] = ""
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import load_movies_json, seed_movies  # noqa: E402
from app.services.gemini import get_llm_client  # noqa: E402


@pytest.fixture(autouse=True)
def database():
    """Database bersih + 20 film untuk SETIAP test (test saling terisolasi)."""
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_movies(db, load_movies_json())
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _auth_headers(client: TestClient, email: str, username: str) -> dict:
    password = "password123"
    r = client.post("/api/auth/register", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture
def user_a(client):
    return _auth_headers(client, "alice@example.com", "alice")


@pytest.fixture
def user_b(client):
    return _auth_headers(client, "bob@example.com", "bob")


class FakeLLM:
    """Gemini palsu: mengembalikan jawaban yang sudah diskenariokan."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[str] = []

    def generate_json(self, system_instruction: str, contents: str) -> str:
        self.calls.append(contents)
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def fake_llm():
    def install(responses):
        fake = FakeLLM(responses)
        app.dependency_overrides[get_llm_client] = lambda: fake
        return fake

    return install
