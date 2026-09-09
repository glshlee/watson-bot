from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_auth_disabled_by_default():
    client = TestClient(app)
    with (
        patch("app.config.settings.WEB_AUTH_ENABLED", False),
        patch("app.config.settings.WEB_AUTH_PASSWORD", ""),
    ):
        res = client.get("/")
        assert res.status_code == 200


def test_auth_enabled_requires_credentials():
    client = TestClient(app)
    with (
        patch("app.config.settings.WEB_AUTH_ENABLED", True),
        patch("app.config.settings.WEB_AUTH_USERNAME", "watson"),
        patch("app.config.settings.WEB_AUTH_PASSWORD", "secret123"),
    ):
        # 1. No credentials -> 401 with WWW-Authenticate
        res_no_auth = client.get("/")
        assert res_no_auth.status_code == 401
        assert "WWW-Authenticate" in res_no_auth.headers
        assert "Basic" in res_no_auth.headers["WWW-Authenticate"]

        # 2. Invalid credentials -> 401
        res_wrong = client.get("/", auth=("watson", "wrongpass"))
        assert res_wrong.status_code == 401

        # 3. Valid credentials -> 200 OK
        res_ok = client.get("/", auth=("watson", "secret123"))
        assert res_ok.status_code == 200

        # 4. Protected API endpoint /api/settings/gtd-path
        res_api_unauth = client.get("/api/settings/gtd-path")
        assert res_api_unauth.status_code == 401

        res_api_ok = client.get("/api/settings/gtd-path", auth=("watson", "secret123"))
        assert res_api_ok.status_code == 200
