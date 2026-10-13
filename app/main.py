import os
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="LostParty API", docs_url=None, redoc_url=None, openapi_url=None)

def connect():
    return psycopg.connect(host="db", dbname=os.environ["POSTGRES_DB"],
                          user="lostparty_app", password=os.environ["APP_DB_PASSWORD"],
                          connect_timeout=3, options="-c statement_timeout=3000")

@app.get("/health")
def health():
    try:
        with connect() as conn:
            value = conn.execute("SELECT 1").fetchone()[0]
        if value != 1:
            raise RuntimeError("Unexpected health result")
    except (psycopg.Error, RuntimeError):
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "unavailable"})
    return {"status": "ok", "database": "ok"}
