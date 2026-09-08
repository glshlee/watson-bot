import json
import os
import shutil
import tempfile

from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_service import AgentService
from app.services.settings_service import SettingsService


def test_settings_service_default_and_set():
    temp_dir = tempfile.mkdtemp()
    temp_config = os.path.join(temp_dir, "gtd_config.json")
    try:
        service = SettingsService(config_file=temp_config)
        default_path = service.get_gtd_path()
        assert os.path.exists(default_path)

        # Set new target directory
        gtd_dir = os.path.join(temp_dir, "custom_gtd")
        status = service.set_gtd_path(gtd_dir, create_if_missing=True)

        assert os.path.exists(gtd_dir)
        assert status["gtd_path"] == gtd_dir
        assert status["exists"] is True
        assert status["is_git_repo"] is False

        # Verify persistence in config file
        assert os.path.exists(temp_config)
        with open(temp_config, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["gtd_path"] == gtd_dir

        # Re-reading should return the persisted path
        service2 = SettingsService(config_file=temp_config)
        assert service2.get_gtd_path() == gtd_dir
    finally:
        shutil.rmtree(temp_dir)


def test_agent_service_gtd_inbox_orchestration():
    temp_dir = tempfile.mkdtemp()
    try:
        # Create gtd folder and inbox.md
        gtd_folder = os.path.join(temp_dir, "gtd")
        os.makedirs(gtd_folder, exist_ok=True)
        inbox_file = os.path.join(gtd_folder, "inbox.md")
        with open(inbox_file, "w", encoding="utf-8") as f:
            f.write("# 📥 GTD Inbox\n\n## 💬 빠른 메모 / 캡처 (Watson & Quick Capture)\n- [ ] 기존 항목\n")

        agent_service = AgentService(base_dir=temp_dir)
        assert agent_service.has_gtd_inbox() is True

        # Append GTD task
        res_file = agent_service.append_or_update_lifelog(
            content="새로운 아이디어 기록",
            category="GTD Inbox",
        )
        assert res_file == inbox_file

        with open(inbox_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "새로운 아이디어 기록" in content
        assert "- [ ] 새로운 아이디어 기록 *(Watson 캡처)*" in content
    finally:
        shutil.rmtree(temp_dir)


def test_agent_service_daily_logs_orchestration():
    temp_dir = tempfile.mkdtemp()
    try:
        # Create logs/daily folder
        daily_folder = os.path.join(temp_dir, "logs", "daily")
        os.makedirs(daily_folder, exist_ok=True)

        agent_service = AgentService(base_dir=temp_dir)
        assert agent_service.has_daily_logs_structure() is True

        from datetime import datetime, timezone
        date_obj = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)

        filepath = agent_service.append_or_update_lifelog(
            content="오늘 아침 미팅 완료",
            category="Daily Notes & Diary",
            date_obj=date_obj,
        )

        assert filepath == os.path.join(daily_folder, "2026-09-08.md")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# 2026-09-08" in content
        assert "오늘 아침 미팅 완료" in content
    finally:
        shutil.rmtree(temp_dir)


def test_settings_api():
    client = TestClient(app)

    # 1. GET /api/settings/gtd-path
    res = client.get("/api/settings/gtd-path")
    assert res.status_code == 200
    data = res.json()
    assert "gtd_path" in data
    assert "is_git_repo" in data

    # 2. POST /api/settings/gtd-path with temp dir
    temp_dir = tempfile.mkdtemp()
    try:
        post_res = client.post(
            "/api/settings/gtd-path",
            json={"path": temp_dir, "create_if_missing": True},
        )
        assert post_res.status_code == 200
        post_data = post_res.json()
        assert post_data["success"] is True
        assert post_data["data"]["gtd_path"] == os.path.abspath(temp_dir)

        # Verify GET reflects new path
        get_res = client.get("/api/settings/gtd-path")
        assert get_res.status_code == 200
        assert get_res.json()["gtd_path"] == os.path.abspath(temp_dir)
    finally:
        shutil.rmtree(temp_dir)
