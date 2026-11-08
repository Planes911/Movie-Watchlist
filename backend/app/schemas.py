"""Request and response schemas. Input validation lives here (via Pydantic)."""

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Movie, Review, Watchlist_Item

def _strip(v):
    """Trim surrounding whitespace so a blank string cannot pass as a value."""
    return v.strip() if isinstance(v, str) else v

class Register_In(BaseModel):
    """Payload for POST /api/auth/register."""
    # Deliberately loose: the frontend derives a default username from the email address.
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    
    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v):
        return _strip(v)

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, v: str) -> str:
        # bcrypt only uses the first 72 BYTES, and non-ASCII characters take more than one byte.
        if len(v.encode("utf-8")) > 72:
            raise ValueError("password maksimal 72 byte")
        return v
    
class Login_In(BaseModel):
    """Payload for POST /api/auth/login."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    
class User_Out(BaseModel):
    """Public user data. Never includes the password hash."""
    # Lets Pydantic read values straight from ORM objects.
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    created_at: datetime
    
class Token_Out(BaseModel):
    """Response of a successful login."""
    token: str
    token_type: str = "bearer"
    user: User_Out
    
class Movie_Out(BaseModel):
    """Movie as returned by the API. Genres and cast are plain lists, matching data/movies.json."""
    id: int
    title: str
    year: int
    director: str
    genres: list[str]
    rating: float
    duration: str
    synopsis: str
    poster_url: str
    cast: list[str]
    
    @classmethod
    def from_model(cls, m: Movie) -> "Movie_Out":
        """Build the API representation from an ORM movie (genre objects become plain names)."""
        return cls(
            id=m.id, title=m.title, year=m.year, director=m.director,
            genres=[g.name for g in m.genres], rating=m.rating, duration=m.duration,
            synopsis=m.synopsis, poster_url=m.poster_url, cast=list(m.cast_members or []),
        )
    
class Recommend_In(BaseModel):
    """Payload for POST /api/movies/recommend (extra fields sent by the frontend are ignored)."""
    prompt: str = Field(min_length=3, max_length=500)

    @field_validator("prompt", mode="before")
    @classmethod
    def strip_prompt(cls, v):
        return _strip(v)
    
class Recommend_Out(BaseModel):
    """The recommended movie id plus the model's explanation."""
    movie_id: int
    reasoning: str
    
class Watchlist_Add_In(BaseModel):
    """Payload for POST /api/watchlist. The spec uses `movieId`; `movie_id` is accepted too."""
    movie_id: int = Field(gt=0, validation_alias=AliasChoices("movieId", "movie_id"))
    
class Watchlist_Out(BaseModel):
    """A watchlist entry together with its movie."""
    id: int
    movie_id: int
    created_at: datetime
    movie: Movie_Out

    @classmethod
    def from_model(cls, item: Watchlist_Item) -> "Watchlist_Out":
        return cls(id=item.id, movie_id=item.movie_id, created_at=item.created_at,
                   movie=Movie_Out.from_model(item.movie))
        
class Watched_In(BaseModel):
    """Payload for POST /api/watched: a 1-5 rating and a written review.

    The frontend sends the review as both `review` and `opinion`, so either key is accepted.
    """
    movie_id: int = Field(gt=0, validation_alias=AliasChoices("movieId", "movie_id"))
    rating: int = Field(ge=1, le=5)
    review: str = Field(min_length=1, max_length=2000, validation_alias=AliasChoices("review", "opinion"))

    @field_validator("review", mode="before")
    @classmethod
    def strip_review(cls, v):
        return _strip(v)
    
class Watched_Out(BaseModel):
    """A watched movie with the user's rating and review."""
    id: int
    movie_id: int
    rating: int
    review: str
    created_at: datetime
    movie: Movie_Out

    @classmethod
    def from_model(cls, r: Review) -> "Watched_Out":
        return cls(id=r.id, movie_id=r.movie_id, rating=r.rating, review=r.review,
                   created_at=r.created_at, movie=Movie_Out.from_model(r.movie))

class Message_Out(BaseModel):
    """Simple confirmation message."""
    message: str
    