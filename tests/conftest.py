from unittest.mock import patch

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def disable_auth_by_default():
    """Ensure tests run with authentication disabled by default,
    unless explicitly enabled in individual tests (e.g., test_auth.py)."""
    with patch.object(settings, "WEB_AUTH_ENABLED", False), patch.object(settings, "WEB_AUTH_PASSWORD", ""):
        yield
