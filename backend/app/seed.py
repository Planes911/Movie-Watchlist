import json
import os
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Genre, Movie
from app.database import Base, engine, SessionLocal

def find_movies_json() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        os.environ.get("MOVIES_JSON_PATH"),
        here.parents[1] / "data" / "movies.json",  # backend/data/movies.json
        here.parents[2] / "data" / "movies.json",  # <repo>/data/movies.json (struktur starter pack)
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    raise FileNotFoundError("movies.json tidak ditemukan. Set MOVIES_JSON_PATH atau letakkan di <repo>/data/.")

def load_movies_json(path: Path | None = None) -> list[dict]:
    with open(path or find_movies_json(), encoding="utf-8") as f:
        return json.load(f)
    
def seed_movies(db: Session, movies: list[dict]):
    existing_ids = set(db.scalars(select(Movie.id)).all())
    genre_cache = {g.name: g for g in db.scalars(select(Genre)).all()}
    created = 0

    for item in movies:
        if item["id"] in existing_ids:
            continue
        genres = []
        for name in item["genres"]:
            genre = genre_cache.get(name)
            if genre is None:
                genre = Genre(name=name)
                db.add(genre)
                genre_cache[name] = genre
            genres.append(genre)
        db.add(
            Movie(
                id=item["id"], title=item["title"], year=item["year"], director=item["director"],
                rating=item["rating"], duration=item["duration"], synopsis=item["synopsis"],
                poster_url=item["poster_url"], cast_members=item["cast"], genres=genres,
            )
        )
        created += 1
    db.commit()
    return created

def sync_postgres_sequence(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text(
            "SELECT setval(pg_get_serial_sequence('movies', 'id'), COALESCE((SELECT MAX(id) FROM movies), 1))"
        ))
        db.commit()
        
def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        created = seed_movies(db, load_movies_json())
        sync_postgres_sequence(db)
        total = db.scalar(select(func.count()).select_from(Movie))
    print(f"Seed selesai: {created} film baru ditambahkan, total {total} film di database.")

if __name__ == "__main__":
    main()