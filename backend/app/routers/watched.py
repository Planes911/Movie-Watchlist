"""Endpoints for movies a user has watched, with a rating and a written review."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.errors import Api_Error
from app.models import Movie, Review, User
from app.schemas import Watched_In, Watched_Out

# Router-level dependency: every route in this file requires a valid token.
router = APIRouter(prefix="/api/watched", tags=["Watched & Reviews"], dependencies=[Depends(get_current_user)])

@router.get("", response_model=list[Watched_Out])
def list_watched(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the current user's watched movies, newest first."""
    stmt = select(Review).where(Review.user_id == user.id).order_by(Review.created_at.desc(), Review.id.desc())
    return [Watched_Out.from_model(r) for r in db.scalars(stmt).all()]

@router.post("", response_model=Watched_Out, status_code=201)
def log_watched(payload: Watched_In, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Record that the current user watched a movie, with a 1-5 rating and a review."""
    movie = db.get(Movie, payload.movie_id)
    if movie is None:
        raise Api_Error(404, "Film tidak ditemukan.")

    # user_id comes from the token, never from the request body.
    review = Review(user_id=user.id, movie_id=movie.id, rating=payload.rating, review=payload.review)
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        # Unique per (user, movie): each user can review a movie only once.
        db.rollback()
        raise Api_Error(409, "Kamu sudah mencatat film ini sebagai ditonton.")
    db.refresh(review)
    return Watched_Out.from_model(review)
