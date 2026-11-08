from sqlalchemy import select
from app.database import SessionLocal
from app.models import Movie
from app.services.gemini import get_llm_client
from app.services import recommender as r

with SessionLocal() as db:
    movies = db.scalars(select(Movie).order_by(Movie.id)).all()
    catalog = [
        {"id": m.id, "title": m.title, "year": m.year,
         "genres": [g.name for g in m.genres], "synopsis": m.synopsis}
        for m in movies
    ]

prompt = r.build_user_prompt("film thriller kriminal dengan plot twist", catalog)
try:
    raw = get_llm_client().generate_json(r.SYSTEM_INSTRUCTION, prompt)
except Exception as e:
    print("GEMINI GAGAL ->", type(e).__name__, e, "| penyebab:", repr(e.__cause__))
    raise SystemExit
print("JAWABAN MENTAH:", repr(raw[:400]))
try:
    print("HASIL VALID:", r.validate_choice(r.parse_llm_json(raw), {m["id"] for m in catalog}))
except Exception as e:
    print("VALIDASI GAGAL ->", type(e).__name__, e)