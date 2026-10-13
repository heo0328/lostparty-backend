import os
import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Literal
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth.router import router
from app.auth.cleanup import run
from app.core.errors import register


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(run())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="LostParty API", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.include_router(router)
register(app)


@app.middleware("http")
async def no_store(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/v1/"):
        response.headers["Cache-Control"] = "no-store"
    return response


_original_openapi = app.openapi
def openapi():
    schema = _original_openapi()
    for path, operations in schema["paths"].items():
        if path.startswith("/v1/"):
            for operation in operations.values():
                operation.get("responses", {}).pop("422", None)
                for status, result in operation.get("responses", {}).items():
                    headers = result.setdefault("headers", {})
                    headers["Cache-Control"] = {"schema": {"type": "string", "const": "no-store"}}
                    if status == "429":
                        headers["Retry-After"] = {"schema": {"type": "integer", "const": 60}}
                    if status == "401":
                        headers["WWW-Authenticate"] = {"schema": {"type": "string", "const": "Bearer"}}
    schema.get("components", {}).get("schemas", {}).pop("HTTPValidationError", None)
    schema.get("components", {}).get("schemas", {}).pop("ValidationError", None)
    schema["x-auth-policy"] = {"challenge_seconds": 300, "access_seconds": 600,
                              "remember_absolute_seconds": 2592000, "remember_idle_seconds": 604800,
                              "memory_absolute_seconds": 43200, "memory_idle_seconds": 7200,
                              "recovery_seconds": 60, "recovery_additional_attempts": 2,
                              "recovery_time_origin": "database clock at final write before successful commit"}
    return schema
app.openapi = openapi

class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]

class UnhealthyResponse(BaseModel):
    status: Literal["unhealthy"]
    database: Literal["unavailable"]

def connect():
    return psycopg.connect(host="db", dbname=os.environ["POSTGRES_DB"],
                          user="lostparty_app", password=os.environ["APP_DB_PASSWORD"],
                          connect_timeout=3, options="-c statement_timeout=3000")

@app.get("/health", response_model=HealthResponse,
         responses={503: {"model": UnhealthyResponse, "description": "Database unavailable"}})
def health():
    try:
        with connect() as conn:
            value = conn.execute("SELECT 1").fetchone()[0]
        if value != 1:
            raise RuntimeError("Unexpected health result")
    except (psycopg.Error, RuntimeError):
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "unavailable"})
    return {"status": "ok", "database": "ok"}
