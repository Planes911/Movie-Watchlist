import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("filmlog")

class Api_Error(Exception):
    def __init__(self, status_code: int, message: str, headers: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.headers = headers
        super().__init__(message)
        
def _body(status_code: int, message: str, **extra) -> dict:
    return {"error": HTTPStatus(status_code).phrase, "message": message, "status": status_code, **extra}

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Api_Error)
    async def _api_error(_: Request, exc: Api_Error):
        return JSONResponse(_body(exc.status_code, exc.message), status_code=exc.status_code, headers=exc.headers)
    
    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        # Menangkap 404 (route tidak ada), 405 (method salah), dsb.
        return JSONResponse(_body(exc.status_code, str(exc.detail)), status_code=exc.status_code, headers=exc.headers)
    
    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
            details.append({"field": ".".join(loc) or "body", "message": str(err.get("msg", ""))})
        summary = "; ".join(f"{d['field']}: {d['message']}" for d in details) or "Request tidak valid."
        return JSONResponse(_body(400, f"Validasi gagal - {summary}", details=details), status_code=400)
    
    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(_body(500, "Terjadi kesalahan pada server."), status_code=500)