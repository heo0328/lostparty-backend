#!/usr/bin/env python3
"""Run from project root. Recreates this project's containers, preserves volumes."""
import json
import subprocess
import uuid
import urllib.request
import urllib.error
from pathlib import Path

def compose(*args, input=None):
    return subprocess.check_output(["docker", "compose", *args], input=input, text=True).strip()

def health(expected=200):
    port = next(line.split("=", 1)[1] for line in Path(".env").read_text().splitlines() if line.startswith("API_PORT="))
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=8) as response:
            status, body = response.status, json.load(response)
    except urllib.error.HTTPError as error:
        status, body = error.code, json.load(error)
    assert status == expected, (status, body)
    print(f"HTTP {status}: {body}")

def sql(statement, params=()):
    code = "from app.main import connect\nwith connect() as c:\n r=c.execute(" + repr(statement) + ", " + repr(params) + ")\n print(r.fetchall() if r.description else 'OK')"
    return compose("exec", "-T", "api", "python", "-c", code)

compose("up", "-d", "--build", "--wait", "--wait-timeout", "180")
health()
assert "False" in sql("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
print("Application role is not a superuser")
token = uuid.uuid4().hex
sql("CREATE TABLE IF NOT EXISTS persistence_probe (token text PRIMARY KEY)")
sql("INSERT INTO persistence_probe(token) VALUES (%s)", (token,))
before = compose("ps", "-q", "db")
compose("stop", "db")
try:
    health(503)
finally:
    compose("up", "-d", "--wait", "--wait-timeout", "180")
health()
compose("down")
compose("up", "-d", "--wait", "--wait-timeout", "180")
after = compose("ps", "-q", "db")
assert before != after, "Database container was not recreated"
assert token in sql("SELECT token FROM persistence_probe WHERE token=%s", (token,))
health()
sql("DELETE FROM persistence_probe WHERE token=%s", (token,))
print("PASS: health, database connection, failure response, non-superuser role, persistence across down/up")
