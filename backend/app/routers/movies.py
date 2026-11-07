import random

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import Api_Error
from app.models import Genre, Movie
from app.schemas import Movie_Out

router = APIRouter(prefix="/api/movies", tags=["Movies"])

def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

@router.get("", response_model=list[Movie_Out])
def list_movies(
    genre: str | None = Query(None, max_length=50, description="Filter genre, mis. Sci-Fi"),
    search: str | None = Query(None, max_length=100, description="Cari di judul / sutradara"),
    shuffle: bool = Query(False, description="Acak urutan hasil"),
    db: Session = Depends(get_db),
):
    stmt = select(Movie).order_by(Movie.id)
    if genre:
        stmt = stmt.where(Movie.genres.any(func.lower(Genre.name) == genre.strip().lower()))
    if search and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        stmt = stmt.where(
            or_(Movie.title.ilike(pattern, escape="\\"), Movie.director.ilike(pattern, escape="\\"))
        )
    movies = list(db.scalars(stmt).all())
    if shuffle:
        random.shuffle(movies)
    return [Movie_Out.from_model(m) for m in movies]

@router.get("/{movie_id}", response_model=Movie_Out)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise Api_Error(404, "Film tidak ditemukan.")
    return Movie_Out.from_model(movie)