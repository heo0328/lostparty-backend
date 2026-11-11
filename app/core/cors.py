"""Explicit browser origins; disabled unless configured by the environment."""
import os

from fastapi.middleware.cors import CORSMiddleware


def register(app):
    origins = [value.strip() for value in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if value.strip()]
    if not origins:
        return
    if "*" in origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must list explicit origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        expose_headers=["Retry-After", "WWW-Authenticate"],
    )
