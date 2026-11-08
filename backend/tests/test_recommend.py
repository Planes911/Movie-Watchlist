"""AI recommendation endpoint, using a scripted fake instead of the real Gemini API."""

from app.services.gemini import LLM_Error

PROMPT = {"prompt": "film sci-fi yang bikin mikir"}
GOOD = '{"movie_id": 14, "reasoning": "Memento bermain dengan memori dan waktu."}'


def test_recommend_success_matches_contract(client, fake_llm):
    fake = fake_llm([GOOD])
    r = client.post("/api/movies/recommend", json=PROMPT)
    assert r.status_code == 200
    assert r.json() == {"movie_id": 14, "reasoning": "Memento bermain dengan memori dan waktu."}
    # Grounding: the whole catalogue from the database must be sent to Gemini.
    sent = fake.calls[0]
    assert all(f"id={i} |" in sent for i in range(1, 21))
    assert "film sci-fi yang bikin mikir" in sent


def test_frontend_extra_fields_are_ignored(client, fake_llm):
    fake_llm([GOOD])
    body = {"prompt": "misteri", "query": "misteri", "description": "misteri"}
    assert client.post("/api/movies/recommend", json=body).status_code == 200


def test_hallucinated_movie_id_is_retried_then_accepted(client, fake_llm):
    fake = fake_llm(['{"movie_id": 999, "reasoning": "film karangan"}', GOOD])
    r = client.post("/api/movies/recommend", json=PROMPT)
    assert r.status_code == 200 and r.json()["movie_id"] == 14
    assert len(fake.calls) == 2 and "ditolak" in fake.calls[1]  # the correction feedback is sent on the retry


def test_hallucination_twice_is_502(client, fake_llm):
    fake_llm(['{"movie_id": 999, "reasoning": "x"}', '{"movie_id": 12345, "reasoning": "y"}'])
    r = client.post("/api/movies/recommend", json=PROMPT)
    assert r.status_code == 502
    assert "message" in r.json()


def test_non_json_answer_is_502(client, fake_llm):
    fake_llm(["Tentu! Saya sarankan Inception.", "Maaf, ini bukan JSON."])
    assert client.post("/api/movies/recommend", json=PROMPT).status_code == 502


def test_llm_failure_is_502(client, fake_llm):
    fake_llm([LLM_Error("kuota habis")])
    assert client.post("/api/movies/recommend", json=PROMPT).status_code == 502


def test_missing_api_key_is_503(client):
    # No override: the real client with an empty GEMINI_API_KEY -> 503 (no network access needed).
    assert client.post("/api/movies/recommend", json=PROMPT).status_code == 503


def test_prompt_validation_is_400(client, fake_llm):
    fake_llm([])
    assert client.post("/api/movies/recommend", json={"prompt": ""}).status_code == 400
    assert client.post("/api/movies/recommend", json={}).status_code == 400
    assert client.post("/api/movies/recommend", json={"prompt": "x" * 501}).status_code == 400
