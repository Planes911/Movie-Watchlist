"""Uniform error format for the whole API.

Every failure is returned as {"error": ..., "message": ..., "status": ...}. The bundled
frontend reads `message` (or `error`), not FastAPI's default `detail` field.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("filmlog")

class Api_Error(Exception):
    """Raised on purpose by our own code: an HTTP status plus a client-safe message."""
    def __init__(self, status_code: int, message: str, headers: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.headers = headers
        super().__init__(message)
        
def _body(status_code: int, message: str, **extra) -> dict:
    """Build the uniform error response body."""
    return {"error": HTTPStatus(status_code).phrase, "message": message, "status": status_code, **extra}

def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers so every error, expected or not, shares the same JSON shape."""
    @app.exception_handler(Api_Error)
    async def _api_error(_: Request, exc: Api_Error):
        return JSONResponse(_body(exc.status_code, exc.message), status_code=exc.status_code, headers=exc.headers)
    
    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        # Covers framework-level errors such as 404 (unknown route) and 405 (wrong method).
        return JSONResponse(_body(exc.status_code, str(exc.detail)), status_code=exc.status_code, headers=exc.headers)
    
    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        # FastAPI answers 422 by default; the API spec asks for 400. Only `loc` and `msg` are copied
        # because exc.errors() can contain objects that are not JSON serializable.
        details = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
            details.append({"field": ".".join(loc) or "body", "message": str(err.get("msg", ""))})
        summary = "; ".join(f"{d['field']}: {d['message']}" for d in details) or "Request tidak valid."
        return JSONResponse(_body(400, f"Validasi gagal - {summary}", details=details), status_code=400)
    
    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        # Full details go to the server log only; clients get a generic message so internals never leak.
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(_body(500, "Terjadi kesalahan pada server."), status_code=500)