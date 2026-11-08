"""Watchlist endpoints, including per-user data isolation."""

def test_add_and_list_watchlist(client, user_a):
    r = client.post("/api/watchlist", json={"movieId": 1}, headers=user_a)
    assert r.status_code == 201
    assert r.json()["movie_id"] == 1
    assert r.json()["movie"]["title"] == "Inception"

    items = client.get("/api/watchlist", headers=user_a).json()
    assert [i["movie_id"] for i in items] == [1]


def test_accepts_snake_case_movie_id_too(client, user_a):
    assert client.post("/api/watchlist", json={"movie_id": 2}, headers=user_a).status_code == 201


def test_duplicate_entry_is_409(client, user_a):
    assert client.post("/api/watchlist", json={"movieId": 1}, headers=user_a).status_code == 201
    r = client.post("/api/watchlist", json={"movieId": 1}, headers=user_a)
    assert r.status_code == 409


def test_unknown_movie_is_404(client, user_a):
    assert client.post("/api/watchlist", json={"movieId": 9999}, headers=user_a).status_code == 404


def test_invalid_body_is_400(client, user_a):
    assert client.post("/api/watchlist", json={"movieId": "abc"}, headers=user_a).status_code == 400
    assert client.post("/api/watchlist", json={"movieId": 0}, headers=user_a).status_code == 400
    assert client.post("/api/watchlist", json={}, headers=user_a).status_code == 400


def test_watchlist_is_private_per_user(client, user_a, user_b):
    client.post("/api/watchlist", json={"movieId": 1}, headers=user_a)
    assert client.get("/api/watchlist", headers=user_b).json() == []


def test_delete_from_watchlist(client, user_a):
    client.post("/api/watchlist", json={"movieId": 1}, headers=user_a)
    assert client.delete("/api/watchlist/1", headers=user_a).status_code == 200
    assert client.get("/api/watchlist", headers=user_a).json() == []
    assert client.delete("/api/watchlist/1", headers=user_a).status_code == 404


def test_user_cannot_delete_another_users_entry(client, user_a, user_b):
    client.post("/api/watchlist", json={"movieId": 1}, headers=user_a)
    assert client.delete("/api/watchlist/1", headers=user_b).status_code == 404
    assert len(client.get("/api/watchlist", headers=user_a).json()) == 1  # A's entry is untouched
