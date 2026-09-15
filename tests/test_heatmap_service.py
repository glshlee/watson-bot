from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.main import app
from app.services.dev_agent_service import DevAgentService
from app.services.heatmap_service import HeatmapService
from app.services.llm_provider import LLMProvider
from app.services.supervisor_service import SupervisorService


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


@pytest.fixture
def temp_gtd_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        daily_dir = os.path.join(tmpdir, "logs", "daily")
        os.makedirs(daily_dir, exist_ok=True)

        # 1. 2026-09-13: 작은 일기 (Level 1)
        with open(os.path.join(daily_dir, "2026-09-13.md"), "w", encoding="utf-8") as f:
            f.write("# 2026-09-13\n\n- [10:00] 짧은 산책 다녀옴.\n")

        # 2. 2026-09-14: 중간 일기 + 완료 태스크 2개 (Level 3)
        with open(os.path.join(daily_dir, "2026-09-14.md"), "w", encoding="utf-8") as f:
            f.write(
                "# 2026-09-14\n\n"
                "## 📝 일기\n"
                "- [09:00] 개발 회의 및 아키텍처 논의를 진행함. 다양한 아이디어가 나와서 유익했다.\n"
                "- [14:00] 코드 리뷰와 리팩토링 수행.\n\n"
                "## ✅ 완료 태스크\n"
                "- [x] 문서 업데이트\n"
                "- [x] 테스트 통과\n"
            )

        # 3. 2026-09-15: 대형 일기 (Level 4)
        with open(os.path.join(daily_dir, "2026-09-15.md"), "w", encoding="utf-8") as f:
            f.write(
                "# 2026-09-15\n\n"
                "## 📝 상세 기록\n"
                + ("오늘 하루 동안 많은 일들을 성실히 해냈다. " * 30)
                + "\n- [x] 잔디 히트맵 개발 완료\n"
            )

        yield tmpdir


def test_heatmap_service_scan(temp_gtd_env):
    service = HeatmapService(base_dir=temp_gtd_env)
    logs = service.scan_all_daily_logs()

    assert "2026-09-13" in logs
    assert "2026-09-14" in logs
    assert "2026-09-15" in logs

    log_14 = logs["2026-09-14"]
    assert log_14["completed_tasks"] == 2
    assert log_14["char_count"] > 50


def test_heatmap_data_and_streaks(temp_gtd_env):
    service = HeatmapService(base_dir=temp_gtd_env)
    data = service.get_heatmap_data(days=30)

    assert "days" in data
    assert "summary" in data
    assert len(data["days"]) == 30

    summary = data["summary"]
    assert summary["total_days_logged"] == 3
    assert summary["total_completed_tasks"] >= 3
    assert summary["longest_streak"] >= 3


def test_get_lifelog_content(temp_gtd_env):
    service = HeatmapService(base_dir=temp_gtd_env)

    # 존재하는 일자
    res_exist = service.get_lifelog_content("2026-09-13")
    assert res_exist["exists"] is True
    assert "짧은 산책" in res_exist["content"]
    assert res_exist["char_count"] > 0

    # 존재하지 않는 일자 -> 기본 템플릿 반환
    res_new = service.get_lifelog_content("2026-09-01")
    assert res_new["exists"] is False
    assert "# 2026-09-01" in res_new["content"]


def test_save_lifelog_content(temp_gtd_env):
    service = HeatmapService(base_dir=temp_gtd_env)

    # 새 일자 저장 (커밋 모킹)
    with patch.object(service.git_service, "commit", return_value=(True, "abc1234")):
        res = service.save_lifelog_content(
            date_str="2026-09-16",
            content="# 2026-09-16\n\n- [08:30] 새로 작성된 로그 내용\n",
            commit_msg="docs: 2026-09-16 일일 로그 작성",
            auto_push=False,
        )

    assert res["success"] is True
    assert res["date"] == "2026-09-16"
    assert res["char_count"] > 10

    # 저장 확인
    verify = service.get_lifelog_content("2026-09-16")
    assert verify["exists"] is True
    assert "새로 작성된 로그 내용" in verify["content"]

    # 잘못된 날짜 포맷 에러
    err_res = service.save_lifelog_content(
        date_str="invalid-date",
        content="some content",
    )
    assert err_res["success"] is False


def test_format_edit_card(temp_gtd_env):
    service = HeatmapService(base_dir=temp_gtd_env)
    card = service.format_edit_card("2026-09-14")
    assert "2026-09-14" in card
    assert "로그 편집" in card or "에디터" in card


def test_web_api_lifelog_endpoints(temp_gtd_env):
    client = TestClient(app)

    with patch("app.services.settings_service.SettingsService.get_gtd_path", return_value=temp_gtd_env):
        # 1. GET /api/lifelog/heatmap
        resp_heatmap = client.get("/api/lifelog/heatmap?days=30")
        assert resp_heatmap.status_code == 200
        json_hm = resp_heatmap.json()
        assert json_hm["status"] == "success"
        assert len(json_hm["data"]["days"]) == 30

        # 2. GET /api/lifelog/file
        resp_file = client.get("/api/lifelog/file?date=2026-09-14")
        assert resp_file.status_code == 200
        json_file = resp_file.json()
        assert json_file["status"] == "success"
        assert "개발 회의" in json_file["data"]["content"]

        # 3. POST /api/lifelog/save
        with patch("app.services.git_service.GitService.commit", return_value=(True, "mockhash")):
            resp_save = client.post(
                "/api/lifelog/save",
                json={
                    "date": "2026-09-17",
                    "content": "# 2026-09-17\n\n- [07:00] 아침 운동 완료\n",
                    "commit_msg": "docs: 2026-09-17 로그 작성",
                    "auto_push": False,
                },
            )
            assert resp_save.status_code == 200
            json_save = resp_save.json()
            assert json_save["status"] == "success"
            assert json_save["data"]["date"] == "2026-09-17"


def test_intent_classification():
    provider = LLMProvider()

    assert provider.analyze_and_respond("/edit").intent == "lifelog_edit"
    assert provider.analyze_and_respond("/edit 2026-09-15").intent == "lifelog_edit"
    assert provider.analyze_and_respond("일기 편집해줘").intent == "lifelog_edit"
    assert provider.analyze_and_respond("오늘 로그 수정하고 싶어").intent == "lifelog_edit"

    assert provider.analyze_and_respond("/heatmap").intent == "lifelog_heatmap"
    assert provider.analyze_and_respond("잔디 보여줘").intent == "lifelog_heatmap"
    assert provider.analyze_and_respond("기여도 히트맵 확인").intent == "lifelog_heatmap"


def test_supervisor_handling_lifelog(db_session, temp_gtd_env):
    supervisor = SupervisorService(db=db_session, base_dir=temp_gtd_env)

    # lifelog_edit
    res_edit = supervisor.process_user_request(
        session_id="test_user_session",
        user_message="/edit 2026-09-15",
        channel="web",
    )
    assert res_edit["intent"] == "lifelog_edit"
    assert "2026-09-15" in res_edit["ai_response"]

    # lifelog_heatmap
    res_hm = supervisor.process_user_request(
        session_id="test_user_session",
        user_message="/heatmap",
        channel="web",
    )
    assert res_hm["intent"] == "lifelog_heatmap"
    assert "잔디" in res_hm["ai_response"] or "히트맵" in res_hm["ai_response"]


def test_dev_agent_lifelog_commands(db_session, temp_gtd_env):
    with patch("app.services.settings_service.SettingsService.get_gtd_path", return_value=temp_gtd_env):
        agent = DevAgentService(db=db_session)

        res_edit = agent.process_dev_request("dev_test_session", "/edit 2026-09-15")
        assert res_edit["action_type"] == "tool_edit"
        assert "2026-09-15" in res_edit["ai_response"]

        res_hm = agent.process_dev_request("dev_test_session", "/heatmap")
        assert res_hm["action_type"] == "tool_heatmap"
        assert "잔디" in res_hm["ai_response"] or "히트맵" in res_hm["ai_response"]
