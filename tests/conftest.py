import os
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

@pytest.fixture(scope='session', autouse=True)
def setup_database():
    assert os.environ['DATABASE_URL'].endswith('/lostparty_test')
    directory = Path(os.environ['AUTH_SECRET_DIR'])
    directory.mkdir(mode=0o700, exist_ok=True)
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    (directory/'jwt.pem').write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (directory/'recovery.key').write_bytes(os.urandom(32))
    subprocess.run(['alembic','upgrade','0001_auth'], check=True, capture_output=True)
    from app.core.database import engine
    import uuid
    existing_id=uuid.uuid4()
    with engine().begin() as c:
        c.execute(text("INSERT INTO users (id,status,created_at,updated_at,last_login_at) VALUES (:id,'active',now(),now(),now())"),{'id':existing_id})
        before=c.execute(text('SELECT * FROM users WHERE id=:id'),{'id':existing_id}).one()
    subprocess.run(['alembic','upgrade','head'], check=True, capture_output=True)
    with engine().connect() as c:
        assert c.execute(text('SELECT * FROM users WHERE id=:id'),{'id':existing_id}).one()==before


@pytest.fixture(autouse=True)
def isolated():
    from app.core.database import engine
    from app.auth.router import _limits
    _limits.clear()
    with engine().begin() as c:
        c.execute(text('TRUNCATE game_account_fetch_leases, game_account_cache, game_account_limit_events, refresh_recoveries, refresh_credentials, auth_sessions, auth_transactions, auth_identities, users CASCADE'))

@pytest.fixture
def client():
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

@pytest.fixture
def login(client, monkeypatch):
    from app.auth import service, tokens
    monkeypatch.setattr(service, 'verify_google', lambda token, nonce: 'same-subject')
    def perform(remember=True):
        secret = tokens.secret()
        r = client.post('/v1/auth/google/challenges', json={'transaction_secret_hash': tokens.digest(secret)})
        assert r.status_code == 201, r.json()
        challenge = r.json()
        request = dict(transaction_id=challenge['transaction_id'], transaction_secret=secret,
                       google_id_token='mock-proof', remember_me=remember)
        r = client.post('/v1/auth/google', json=request)
        assert r.status_code == 200, r.json()
        return r.json(), request
    return perform
