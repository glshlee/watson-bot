from __future__ import annotations

import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.main import app
from app.services.dev_agent_service import DevAgentService
from app.services.setup_service import SetupService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_setup_service_mask_secret():
    assert SetupService._mask_secret("") == ""
    assert SetupService._mask_secret("1234") == "******"
    masked = SetupService._mask_secret("1234567890abcdef", show_chars=4)
    assert masked.startswith("1234...")
    assert masked.endswith("cdef")


def test_setup_service_status_structure():
    service = SetupService()
    status = service.get_setup_status()

    assert "is_ready" in status
    assert "readiness_percentage" in status
    assert "checks" in status
    assert "telegram_bot" in status["checks"]
    assert "telegram_admin" in status["checks"]
    assert "llm_engine" in status["checks"]
    assert "gtd_storage" in status["checks"]
    assert "web_auth" in status["checks"]
    assert "commute_briefing" in status["checks"]
    assert "runtime" in status["checks"]


def test_setup_service_format_report():
    service = SetupService()
    report = service.format_status_report()

    assert "Watson 시스템 설정 & 배포 상태 진단" in report
    assert "준비율" in report
    assert "텔레그램 봇 토큰" in report
    assert "GTD 저장소" in report


def test_web_api_setup_status():
    client = TestClient(app)
    res = client.get("/api/system/setup-status")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["status"] == "success"
    assert "data" in json_data
    assert "report" in json_data
    assert json_data["data"]["total_checks"] >= 7


def test_dev_agent_setup_command(db_session):
    agent = DevAgentService(db=db_session)
    res = agent.process_dev_request("dev_setup_session", "/setup")
    assert res["action_type"] == "tool_setup"
    assert "Watson 시스템 설정 & 배포 상태 진단" in res["ai_response"]


def test_setup_wizard_script_dry_run():
    result = subprocess.run(
        ["./scripts/setup_wizard.sh", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    assert "Dry-run 모의 셋업 검증 완료" in result.stdout


def test_setup_wizard_script_check():
    result = subprocess.run(
        ["./scripts/setup_wizard.sh", "--check"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    assert "시스템 설정 및 준비 상태를 점검합니다" in result.stdout
