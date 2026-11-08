"""Movie catalogue endpoints plus the AI recommendation endpoint."""

import random
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import Api_Error
from app.models import Genre, Movie
from app.schemas import Movie_Out, Recommend_In, Recommend_Out
from app.services.gemini import LLM_Client, LLM_Error, LLM_Not_Configured_Error, get_llm_client
from app.services.recommender import Recommendation_Error, recommend_movie

router = APIRouter(prefix="/api/movies", tags=["Movies"])
logger = logging.getLogger("filmlog")

def _escape_like(text: str) -> str:
    """Escape LIKE wildcards so user input is matched literally (searching for '%' finds nothing)."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

@router.get("", response_model=list[Movie_Out])
def list_movies(
    genre: str | None = Query(None, max_length=50, description="Filter genre, mis. Sci-Fi"),
    search: str | None = Query(None, max_length=100, description="Cari di judul / sutradara"),
    shuffle: bool = Query(False, description="Acak urutan hasil"),
    db: Session = Depends(get_db),
):
    """List movies. Optional filters: genre (case-insensitive), search (title or director), shuffle."""
    stmt = select(Movie).order_by(Movie.id)
    if genre:
        # EXISTS subquery on the many-to-many relation; the genre match is case-insensitive.
        stmt = stmt.where(Movie.genres.any(func.lower(Genre.name) == genre.strip().lower()))
    if search and search.strip():
        # Case-insensitive substring match on title or director.
        pattern = f"%{_escape_like(search.strip())}%"
        stmt = stmt.where(
            or_(Movie.title.ilike(pattern, escape="\\"), Movie.director.ilike(pattern, escape="\\"))
        )
    movies = list(db.scalars(stmt).all())
    if shuffle:
        random.shuffle(movies)
    return [Movie_Out.from_model(m) for m in movies]

# Declared before '/{movie_id}' so the static path is matched first. Public on purpose (per the
# assignment); in production, add rate limiting to protect the Gemini quota.
@router.post("/recommend", response_model=Recommend_Out)
def recommend(
    payload: Recommend_In,
    db: Session = Depends(get_db),
    llm: LLM_Client = Depends(get_llm_client),
):
    """Recommend one movie from the local catalogue using Gemini.

    The model only sees movies that exist in our database (grounding) and its answer is
    validated before being returned. See app/services/recommender.py.
    """
    movies = db.scalars(select(Movie).order_by(Movie.id)).all()
    # Compact catalogue sent to the model: just what it needs in order to choose.
    catalog = [
        {"id": m.id, "title": m.title, "year": m.year, "genres": [g.name for g in m.genres], "synopsis": m.synopsis}
        for m in movies
    ]
    try:
        return recommend_movie(payload.prompt, catalog, llm)
    # 503: the feature is unavailable because the server is not configured.
    except LLM_Not_Configured_Error:
        raise Api_Error(503, "Fitur rekomendasi AI belum dikonfigurasi (GEMINI_API_KEY kosong).")
    except (LLM_Error, Recommendation_Error) as exc:
        # 502: our server is healthy but the upstream AI service failed or gave an unusable answer.
        # Details go to the log only, never to the client.
        logger.error("Rekomendasi gagal: %s", exc)
        raise Api_Error(502, "Layanan AI gagal memberi rekomendasi yang valid. Coba lagi sebentar.")

@router.get("/{movie_id}", response_model=Movie_Out)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    """Return a single movie, or 404 if it does not exist."""
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise Api_Error(404, "Film tidak ditemukan.")
    return Movie_Out.from_model(movie)
