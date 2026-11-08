"""Database models (ERD overview).

    users  1 --- *  watchlists  * --- 1  movies
    users  1 --- *  reviews     * --- 1  movies
    movies * --- *  genres      (through the movie_genres association table)
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

def utcnow() -> datetime:
    """Timezone-aware UTC timestamp, used as the default for created_at columns."""
    return datetime.now(timezone.utc)

# Association table for the many-to-many relation between movies and genres.
movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, index=True)
)

class User(Base):
    """A registered account."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    # Display name only (the frontend derives it from the email), so it is intentionally not unique.
    # Identity for login is the unique email.
    username: Mapped[str] = mapped_column(String(50))
    # Unique and indexed: login looks users up by email.
    email: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    # bcrypt hash; the plain-text password is never stored.
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Genre(Base):
    """A movie genre (e.g. Sci-Fi)."""
    __tablename__ = "genres"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

class Movie(Base):
    """A movie in the catalogue, seeded from data/movies.json."""
    __tablename__ = "movies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    year: Mapped[int] = mapped_column(Integer)
    director: Mapped[str] = mapped_column(String(255))
    rating: Mapped[float] = mapped_column(Float)
    duration: Mapped[str] = mapped_column(String(50))
    synopsis: Mapped[str] = mapped_column(Text)
    poster_url: Mapped[str] = mapped_column(Text)
    # The cast list is only displayed, never queried, so a JSON column is enough.
    cast_members: Mapped[list] = mapped_column(JSON, default=list)
    # Normalised many-to-many so genre filtering is a real query; selectin loading avoids N+1 queries.
    genres: Mapped[list["Genre"]] = relationship(
        secondary=movie_genres, order_by="Genre.name", lazy="selectin"
    )
    
class Watchlist_Item(Base):
    """A movie a user wants to watch later.

    Rows are removed automatically (ON DELETE CASCADE) when the user or the movie is deleted,
    and the movie is joined-loaded so listing a watchlist needs a single query.
    """
    __tablename__ = "watchlists"
    
    # A movie can be on a user's watchlist only once. The database enforces it, so the rule also
    # holds for concurrent requests (the API turns the violation into a 409).
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_watchlist_user_movie"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    movie: Mapped["Movie"] = relationship(lazy="joined")

class Review(Base):
    """A user's rating and written opinion for a movie they have watched."""
    __tablename__ = "reviews"
    # One review per user and movie. The CHECK constraint backs up the API validation, so an
    # invalid rating can never reach the table.
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_review_user_movie"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    review: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    movie: Mapped["Movie"] = relationship(lazy="joined")