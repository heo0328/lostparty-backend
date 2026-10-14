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
from app.game_accounts.router import router as game_router
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
app.include_router(game_router)
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
                        headers["Retry-After"] = {"schema": {"type": "integer", "minimum": 1}} if "game-accounts" in operation.get("tags", []) else {"schema": {"type": "integer", "const": 60}}
                    if status == "409" and "game-accounts" in operation.get("tags", []):
                        headers["Retry-After"] = {"description": "REQUEST_IN_PROGRESS only", "schema": {"type": "integer", "const": 2}}
                    if status == "401":
                        headers["WWW-Authenticate"] = {"schema": {"type": "string", "const": "Bearer"}}
    schema.get("components", {}).get("schemas", {}).pop("HTTPValidationError", None)
    schema.get("components", {}).get("schemas", {}).pop("ValidationError", None)
    schema["x-auth-policy"] = {"challenge_seconds": 300, "access_seconds": 600,
                              "remember_absolute_seconds": 2592000, "remember_idle_seconds": 604800,
                              "memory_absolute_seconds": 43200, "memory_idle_seconds": 7200,
                              "recovery_seconds": 60, "recovery_additional_attempts": 2,
                              "recovery_time_origin": "database clock at final write before successful commit"}
    schema['x-game-account-policy'] = {
        'idempotency': {'key': 'UUIDv4', 'scope': 'actor + operation',
                        'hash': 'normalized method/path target/query/body',
                        'result_seconds': 86400, 'tombstone_seconds': 86400,
                        'lease_seconds': 30, 'generation_fencing': True,
                        'in_progress_status': 409, 'retry_after_seconds': 2,
                        'delete_replay': 'same actor saved 204; live row not required',
                        'failure_retry': 'same key/hash after retryable failure or lease expiry',
                        'pending_confirm_replay': 'original observation; new explicit check uses new key'},
        'challenge_seconds': 600, 'representative_cooldown_seconds': 300,
        'first_representative_starts_cooldown': False,
        'max_registrations': 20, 'max_characters': 200,
        'page_default': 50, 'page_max': 100,
        'preview_seconds': 1800, 'preview_cleanup_grace_seconds': 3600,
        'terminal_challenge_retention_seconds': 86400, 'audit_seconds': 7776000,
        'rate_limits': {'shared_backend': 'PostgreSQL rolling windows',
                        'provider_per_minute': 80, 'start_actor_per_minute': 3,
                        'confirm_actor_per_minute': 12, 'confirm_interval_seconds': 5,
                        'manual_refresh_interval_seconds': 10,
                        'transport_concurrency': '2 per process'},
        'pagination': 'full settings on every page; compare roster/settings/ownership versions across pages',
        'registration_label': {'automatic_value': '', 'post_omitted': 'empty string',
                               'patch_omitted': 'unchanged', 'explicit_null': 'rejected',
                               'normalization': 'trim surrounding whitespace; max 40 characters',
                               'display': 'Flutter calculates 메인 계정 / 부계정 N from current is_main and full registration order',
                               'subaccount_order': 'created_at ascending, registration_id ascending; custom labels count toward numbering',
                               'main_switch': 'labels unchanged; refetch full registration list'},
        'live_evidence': 'equipment schema proof not validated; live ownership confirmation held pending',
        'live_roster_decrease': 'suspect only; missing/transfer require validated observation criteria',
        'mutation_locking': 'initial global game transaction advisory lock; no network under lock',
    }
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
