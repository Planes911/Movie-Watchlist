"""Create the database tables and seed the initial movies.

Run from the backend/ folder:  python -m app.seed
Safe to run repeatedly (idempotent): movies that already exist are skipped.
"""

import json
import os
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Genre, Movie
from app.database import Base, engine, SessionLocal

def find_movies_json() -> Path:
    """Locate movies.json: env override first, then backend/data/, then <repo>/data/."""
    here = Path(__file__).resolve()
    candidates = [
        os.environ.get("MOVIES_JSON_PATH"),
        here.parents[1] / "data" / "movies.json",  # backend/data/movies.json
        here.parents[2] / "data" / "movies.json",  # <repo>/data/movies.json (starter pack layout)
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    raise FileNotFoundError("movies.json tidak ditemukan. Set MOVIES_JSON_PATH atau letakkan di <repo>/data/.")

def load_movies_json(path: Path | None = None) -> list[dict]:
    """Read the seed movies from the JSON file shipped with the starter pack."""
    with open(path or find_movies_json(), encoding="utf-8") as f:
        return json.load(f)
    
def seed_movies(db: Session, movies: list[dict]):
    """Insert the movies that are not in the database yet.

    Returns the number of newly created movies (0 when everything already exists).
    """
    existing_ids = set(db.scalars(select(Movie.id)).all())
    # Cache genres by name so each genre row is created only once.
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
    """Align PostgreSQL's id sequence with the seeded rows.

    Seeding inserts explicit ids (1..N), which does not advance the sequence; without
    this, the next auto-generated id would collide with an existing primary key.
    """
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text(
            "SELECT setval(pg_get_serial_sequence('movies', 'id'), COALESCE((SELECT MAX(id) FROM movies), 1))"
        ))
        db.commit()
        
def main() -> None:
    """Create missing tables, then seed the movies."""
    # create_all only creates missing tables and never alters existing ones. For schema changes in
    # production, use a migration tool such as Alembic.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        created = seed_movies(db, load_movies_json())
        sync_postgres_sequence(db)
        total = db.scalar(select(func.count()).select_from(Movie))
    print(f"Seed selesai: {created} film baru ditambahkan, total {total} film di database.")

if __name__ == "__main__":
    main()
    