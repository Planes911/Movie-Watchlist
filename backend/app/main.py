from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_exception_handlers
from app.routers import movies

settings = get_settings()

app = FastAPI(
    title="Filmlog API",
    version="1.0.0",
    description="REST API watchlist & review film dengan rekomendasi Gemini (grounded ke database lokal).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(movies.router)

@app.get("/api/health", tags=["Meta"])
def health():
    return {"status": "ok"}