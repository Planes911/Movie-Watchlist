"""Application settings, loaded from environment variables (or a local .env file).

Secrets such as JWT_SECRET and GEMINI_API_KEY never live in the source code.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Defaults to a local SQLite file; set a PostgreSQL URL (e.g. Supabase) for deployment.
    database_url: str = "sqlite:///./filmlog.db"
    
    # No default on purpose: the app refuses to start without a secret (fail fast).
    jwt_secret: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # bcrypt work factor. 12 is a sound default; the test suite lowers it to stay fast.
    bcrypt_rounds: int = 12

    gemini_api_key: str = ""
    # Model names change often, so the model is configurable through GEMINI_MODEL.
    gemini_model: str = "gemini-3.8-flash"

    cors_origins: str = "*"
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        # Hosting providers hand out `postgres://` or `postgresql://` URLs, while SQLAlchemy with
        # psycopg v3 expects the `postgresql+psycopg://` scheme.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS value into a clean list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    
@lru_cache()
def get_settings() -> Settings:
    """Cached accessor: settings (and the .env file) are parsed only once."""
    return Settings()
