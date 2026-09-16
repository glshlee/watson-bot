from unittest.mock import patch

import pytest

from app.config import settings
from app.services.dev_agent_service import DevAgentService
from app.services.llm_provider import LLMProvider


@pytest.fixture(autouse=True)
def disable_auth_by_default():
    """Ensure tests run with authentication disabled by default,
    unless explicitly enabled in individual tests (e.g., test_auth.py)."""
    with patch.object(settings, "WEB_AUTH_ENABLED", False), patch.object(settings, "WEB_AUTH_PASSWORD", ""):
        yield


@pytest.fixture(autouse=True)
def fast_unit_test_environment():
    """Mock external CLI processes and heavy dev subprocesses during unit tests
    to achieve instant execution (< 10 seconds). End-to-end integration and real
    CLI flows are validated via ./scripts/smoke_test.sh."""
    mock_lint = {
        "all_passed": True,
        "ruff_ok": True,
        "ruff_out": "All checks passed!",
        "mypy_ok": True,
        "mypy_out": "Success: no issues found in 30 source files",
    }
    mock_test = {
        "success": True,
        "target": "tests/test_auth.py",
        "output": "pytest tests/test_auth.py .. [100%]\n2 passed in 0.05s",
        "returncode": 0,
    }

    with patch.object(LLMProvider, "_find_agy_path", return_value=None), \
         patch.object(DevAgentService, "_run_lint", return_value=mock_lint), \
         patch.object(DevAgentService, "_run_pytest", return_value=mock_test):
        yield

