from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_web_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Watson - 24/7 AI Agent Console" in response.text

def test_api_chat_endpoint():
    response = client.post(
        "/api/chat",
        json={
            "session_id": "test_chat_session",
            "message": "Testing interactive AI chat console endpoint",
            "category": "Daily Notes & Diary",
            "auto_push": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test_chat_session"
    assert "filepath" in data
    assert "ai_response" in data

def test_get_sessions_and_history():
    res_sessions = client.get("/api/sessions")
    assert res_sessions.status_code == 200

    res_history = client.get("/api/sessions/test_chat_session/history")
    assert res_history.status_code == 200
    data = res_history.json()
    assert data["session_id"] == "test_chat_session"
    assert len(data["history"]) >= 2


def test_session_management_endpoints():
    session_id = "test_endpoint_session"

    # 1. Initialize session via chat
    res_chat = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "안녕 왓슨 오늘 하루 시작",
            "category": "Daily Notes & Diary",
            "auto_push": False
        }
    )
    assert res_chat.status_code == 200

    # 2. Rename session
    res_rename = client.patch(
        f"/api/sessions/{session_id}",
        json={"title": "하루 시작 세션"}
    )
    assert res_rename.status_code == 200
    assert res_rename.json()["title"] == "하루 시작 세션"

    # 3. Rename with empty title -> 400
    res_rename_fail = client.patch(
        f"/api/sessions/{session_id}",
        json={"title": "   "}
    )
    assert res_rename_fail.status_code == 400

    # 4. Clear session messages
    res_clear = client.post(f"/api/sessions/{session_id}/clear")
    assert res_clear.status_code == 200

    res_history_cleared = client.get(f"/api/sessions/{session_id}/history")
    assert res_history_cleared.status_code == 200
    assert len(res_history_cleared.json()["history"]) == 0

    # 5. Delete session
    res_del = client.delete(f"/api/sessions/{session_id}")
    assert res_del.status_code == 200

    # 6. Delete non-existent session -> 404
    res_del_404 = client.delete(f"/api/sessions/{session_id}")
    assert res_del_404.status_code == 404


def test_health_check_endpoints():
    """ADR-021: 초경량 헬스체크 및 하트비트 엔드포인트 검증."""
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data = res_health.json()
    assert data["status"] == "ok"
    assert data["service"] == "watson"
    assert "timestamp" in data

    res_healthz = client.get("/healthz")
    assert res_healthz.status_code == 200
    assert res_healthz.json()["status"] == "ok"


def test_get_briefing_endpoint():
    """ADR-024: 아침/저녁 GTD 브리핑 REST 엔드포인트 검증."""
    res_morning = client.get("/api/briefing?mode=morning")
    assert res_morning.status_code == 200
    data_m = res_morning.json()
    assert data_m["status"] == "success"
    assert data_m["data"]["mode"] == "morning"
    assert "Watson Morning Briefing" in data_m["data"]["markdown"]

    res_evening = client.get("/api/briefing?mode=evening")
    assert res_evening.status_code == 200
    data_e = res_evening.json()
    assert data_e["status"] == "success"
    assert data_e["data"]["mode"] == "evening"
    assert "Watson Evening Briefing" in data_e["data"]["markdown"]


def test_get_briefing_schedule_endpoint():
    """ADR-025: 브리핑 정기 스케줄 및 오늘 일정 REST 엔드포인트 검증."""
    res = client.get("/api/briefing/schedule")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "current_time" in data["data"]
    assert "schedules" in data["data"]
    assert len(data["data"]["schedules"]) == 2
    assert "today_schedules" in data["data"]
    assert "telegram_push" in data["data"]


def test_briefing_scheduler_endpoints():
    """ADR-026: 정기 브리핑 스케줄러 상태 및 푸시 트리거 엔드포인트 검증."""
    # 1. Scheduler status
    res_status = client.get("/api/briefing/scheduler/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["status"] == "success"
    assert status_data["data"]["morning_time"] == "08:30 KST"
    assert status_data["data"]["evening_time"] == "20:00 KST"

    # 2. Trigger push (using mock / safe test)
    res_trigger = client.post(
        "/api/briefing/trigger-push",
        json={"mode": "morning"}
    )
    assert res_trigger.status_code == 200
    trigger_data = res_trigger.json()
    assert trigger_data["status"] == "success"
    assert "sent_count" in trigger_data["data"]



