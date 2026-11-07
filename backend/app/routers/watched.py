from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.errors import Api_Error
from app.models import Movie, Review, User
from app.schemas import Watched_In, Watched_Out

router = APIRouter(prefix="/api/watched", tags=["Watched & Reviews"], dependencies=[Depends(get_current_user)])

@router.get("", response_model=list[Watched_Out])
def list_watcher(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Review).where(Review.user_id == user.id).order_by(Review.created_at.desc(), Review.id.desc())
    return [Watched_Out.from_model(r) for r in db.scalars(stmt).all()]

@router.post("", response_model=Watched_Out, status_code=201)
def log_watched(payload: Watched_In, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    movie = db.get(Movie, payload.movie_id)
    if movie is None:
        raise Api_Error(404, "Film tidak ditemukan.")

    review = Review(user_id=user.id, movie_id=movie.id, rating=payload.rating, review=payload.review)
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Api_Error(409, "Kamu sudah mencatat film ini sebagai ditonton.")
    db.refresh(review)
    return Watched_Out.from_model(review)