"""Application entry point: wires up CORS, error handlers and routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_exception_handlers
from app.routers import movies, auth, watchlist, watched

# Fails fast at startup if required settings (e.g. JWT_SECRET) are missing.
settings = get_settings()

app = FastAPI(
    title="Filmlog API",
    version="1.0.0",
    description="REST API watchlist & review film dengan rekomendasi Gemini (grounded ke database lokal).",
)

# Authentication uses the Authorization header rather than cookies, so allowing all origins is
# safe here. Set CORS_ORIGINS to the frontend's origin to tighten it in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uniform JSON error format for every failure.
register_exception_handlers(app)

# Every router must be registered here; otherwise its endpoints answer 404.
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(watchlist.router)
app.include_router(watched.router)

@app.get("/api/health", tags=["Meta"])
def health():
    """Lightweight liveness probe (does not touch the database)."""
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
def root():
    """Landing route so the bare URL is not a 404."""
    return {"name": "FilmLog API", "docs": "/docs", "health": "/api/health"}