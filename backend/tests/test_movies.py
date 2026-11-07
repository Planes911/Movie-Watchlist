def test_list_movies_returns_seeded_20_with_contract_shape(client):
    r = client.get("/api/movies")
    assert r.status_code == 200
    movies = r.json()
    assert len(movies) == 20
    first = movies[0]
    assert set(first) == {"id", "title", "year", "director", "genres", "rating",
                          "duration", "synopsis", "poster_url", "cast"}
    assert isinstance(first["genres"], list) and isinstance(first["cast"], list)


def test_filter_by_genre_is_case_insensitive(client):
    movies = client.get("/api/movies", params={"genre": "sci-fi"}).json()
    assert movies
    assert all("Sci-Fi" in m["genres"] for m in movies)


def test_search_matches_title_and_director(client):
    assert [m["title"] for m in client.get("/api/movies", params={"search": "inception"}).json()] == ["Inception"]
    by_director = client.get("/api/movies", params={"search": "nolan"}).json()
    assert by_director and all("Nolan" in m["director"] for m in by_director)


def test_search_treats_like_wildcards_as_plain_text(client):
    assert client.get("/api/movies", params={"search": "%"}).json() == []


def test_shuffle_keeps_same_movies(client):
    plain = {m["id"] for m in client.get("/api/movies").json()}
    shuffled = {m["id"] for m in client.get("/api/movies", params={"shuffle": "true"}).json()}
    assert plain == shuffled


def test_get_movie_detail(client):
    r = client.get("/api/movies/14")
    assert r.status_code == 200
    assert r.json()["title"] == "Memento"


def test_unknown_movie_is_404_and_bad_id_is_400(client):
    r = client.get("/api/movies/9999")
    assert r.status_code == 404
    assert "message" in r.json()
    assert client.get("/api/movies/abc").status_code == 400
