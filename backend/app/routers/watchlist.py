"""Watchlist endpoints (all of them require a valid token)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.errors import Api_Error
from app.models import Watchlist_Item, Movie, User
from app.schemas import Message_Out, Watchlist_Add_In, Watchlist_Out

# Router-level dependency: every route in this file requires a valid token, even if a future
# endpoint forgets to ask for the user explicitly.
router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"], dependencies=[Depends(get_current_user)])

@router.get("", response_model=list[Watchlist_Out])
def get_watchlist(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the current user's watchlist, newest first."""
    stmt = (
        select(Watchlist_Item)
        # The user id always comes from the verified token, never from client input, so users can
        # only ever see their own data.
        .where(Watchlist_Item.user_id == user.id)
        .order_by(Watchlist_Item.created_at.desc(), Watchlist_Item.id.desc())
    )
    return [Watchlist_Out.from_model(i) for i in db.scalars(stmt).all()]

@router.post("", response_model=Watchlist_Out, status_code=201)
def add_to_watchlist(
    payload: Watchlist_Add_In, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Add a movie to the current user's watchlist (404 unknown movie, 409 duplicate)."""
    movie = db.get(Movie, payload.movie_id)
    if movie is None:
        raise Api_Error(404, "Film tidak ditemukan.")

    item = Watchlist_Item(user_id=user.id, movie_id=movie.id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        # Raised by the (user_id, movie_id) unique constraint: already on the list.
        db.rollback()
        raise Api_Error(409, "Film sudah ada di watchlist kamu.")
    db.refresh(item)
    return Watchlist_Out.from_model(item)
    
@router.delete("/{movie_id}", response_model=Message_Out)
def remove_from_watchlist(movie_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove a movie from the current user's watchlist."""
    item = db.scalar(
        select(Watchlist_Item).where(Watchlist_Item.user_id == user.id, Watchlist_Item.movie_id == movie_id)
    )
    if item is None:
        # Someone else's entry also yields 404 (not 403), so its existence is never revealed.
        raise Api_Error(404, "Film tidak ada di watchlist kamu.")
    db.delete(item)
    db.commit()
    return Message_Out(message="Film dihapus dari watchlist.")
