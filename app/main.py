import os
from typing import Literal
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="LostParty API", docs_url=None, redoc_url=None, openapi_url=None)

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
