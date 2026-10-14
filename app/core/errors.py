import uuid
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError


class AuthError(Exception):
    def __init__(self, code, status=401):
        self.code, self.status = code, status


def response(request, code, status, retry_after=None):
    request_id = str(uuid.uuid4())
    if status >= 400:
        logging.getLogger(__name__).warning("API rejected code=%s status=%s request_id=%s", code, status, request_id)
    headers = {"Cache-Control": "no-store"}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if status == 429:
        headers["Retry-After"] = "60"
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(status_code=status, headers=headers,
                        content={"error": {"code": code, "message": code,
                                  "request_id": request_id}})


def register(app):
    @app.exception_handler(AuthError)
    async def auth_error(request: Request, error: AuthError):
        return response(request, error.code, error.status, getattr(error, "retry_after", None))

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, error: RequestValidationError):
        # Do not return Pydantic's input field: it may contain credentials.
        return response(request, "INVALID_REQUEST", 400)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, error: SQLAlchemyError):
        return response(request, "SERVICE_UNAVAILABLE", 503)
