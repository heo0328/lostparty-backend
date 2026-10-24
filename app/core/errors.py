import uuid
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.core.observability import emit, category, RequestLoggingMiddleware


class AuthError(Exception):
    def __init__(self, code, status=401):
        self.code, self.status = code, status


def response(request, code, status, retry_after=None, retry_at=None, request_id=None):
    request_id = request_id or getattr(request.state, "log_request_id", None) or str(uuid.uuid4())
    request.state.log_request_id = request_id
    if status >= 400:
        emit("api_rejected", level=logging.WARNING, code=code, status=status, request_id=request_id)
    headers = {"Cache-Control": "no-store"}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if status == 429:
        headers["Retry-After"] = "60"
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    detail = {"code": code, "message": code, "request_id": request_id}
    if retry_at is not None and code in ('RATE_LIMITED', 'UPSTREAM_RATE_LIMITED'):
        detail.update(retry_after_seconds=retry_after, retry_at=retry_at.isoformat())
    return JSONResponse(status_code=status, headers=headers, content={"error": detail})


def register(app):
    app.add_middleware(RequestLoggingMiddleware)
    @app.exception_handler(AuthError)
    async def auth_error(request: Request, error: AuthError):
        return response(request, error.code, error.status, getattr(error, "retry_after", None), getattr(error, "retry_at", None), getattr(error, "request_id", None))

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, error: RequestValidationError):
        # Do not return Pydantic's input field: it may contain credentials.
        return response(request, "INVALID_REQUEST", 400)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, error: SQLAlchemyError):
        emit("database_error", level=logging.ERROR, category=category(error))
        return response(request, "SERVICE_UNAVAILABLE", 503)
