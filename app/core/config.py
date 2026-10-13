import os
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import URL


@dataclass(frozen=True)
class Settings:
    google_audience: str = os.getenv("GOOGLE_CLIENT_ID", "574337852234-vdkvdobbq8es2rdpumc1icqt6ja3a3cr.apps.googleusercontent.com")
    google_azp: tuple = tuple(filter(None, os.getenv("GOOGLE_AZP_ALLOWLIST", "").split(",")))
    issuer: str = "lostparty-backend"
    audience: str = "lostparty-app"
    jwt_kid: str = os.getenv("JWT_KEY_ID", "local-1")
    recovery_kid: str = os.getenv("RECOVERY_KEY_ID", "local-1")
    secret_dir: str = os.getenv("AUTH_SECRET_DIR", "/run/secrets")

    def signing_key(self):
        return Path(self.secret_dir, "jwt.pem").read_bytes()

    def recovery_key(self, key_id=None):
        key_id = key_id or self.recovery_kid
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key_id):
            raise ValueError("Invalid key identifier")
        name = "recovery.key" if key_id == self.recovery_kid else f"recovery-{key_id}.key"
        key = Path(self.secret_dir, name).read_bytes()
        if len(key) != 32:
            raise ValueError("Invalid key configuration")
        return key


settings = Settings()


def database_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    return URL.create("postgresql+psycopg", username="lostparty_app",
                      password=os.environ["APP_DB_PASSWORD"], host="db",
                      database=os.environ["POSTGRES_DB"])
