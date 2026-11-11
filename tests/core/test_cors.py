"""Browser transport checks without database/startup or real credentials.

Run with python -m unittest tests.core.test_cors (no DB fixtures).
"""
import importlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class CorsTests(unittest.TestCase):
    def clients(self, origins="http://localhost:3000"):
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": origins}):
            import app.main
            module = importlib.reload(app.main)
            return [TestClient(module.app), TestClient(module.create_two_cycle_app())]

    def test_preflight_and_auth_error_on_both_profiles(self):
        for client in self.clients():
            with self.subTest(profile=client.app):
                response = client.options("/v1/me", headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "PUT",
                    "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")
                self.assertNotIn("access-control-allow-credentials", response.headers)
                response = client.get("/v1/me", headers={"Origin": "http://localhost:3000"})
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertIn("Retry-After", response.headers["access-control-expose-headers"])
                self.assertIn("WWW-Authenticate", response.headers["access-control-expose-headers"])

    def test_unapproved_origin_and_header(self):
        for client in self.clients():
            for origin, header in [("http://localhost:3001", "authorization"),
                                   ("http://localhost:3000", "x-unapproved")]:
                response = client.options("/v1/me", headers={
                    "Origin": origin, "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": header,
                })
                self.assertEqual(response.status_code, 400)
                if origin.endswith("3001"):
                    self.assertNotIn("access-control-allow-origin", response.headers)

    def test_disabled_and_nonbrowser_auth_preserved(self):
        for client in self.clients(""):
            response = client.get("/v1/me", headers={"Origin": "http://localhost:3000"})
            self.assertEqual(response.status_code, 401)
            self.assertNotIn("access-control-allow-origin", response.headers)
        for client in self.clients():
            response = client.get("/v1/me")
            self.assertEqual(response.status_code, 401)
            self.assertNotIn("access-control-allow-origin", response.headers)

    def test_wildcard_rejected(self):
        from fastapi import FastAPI
        from app.core.cors import register
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*"}):
            with self.assertRaises(ValueError):
                register(FastAPI())
