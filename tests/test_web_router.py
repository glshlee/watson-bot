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

