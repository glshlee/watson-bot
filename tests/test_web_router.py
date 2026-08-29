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
