from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_web_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Watson - 24/7 GitHub LifeLog AI Agent" in response.text

def test_api_log_endpoint():
    response = client.post(
        "/api/log",
        json={
            "session_id": "test_web_session",
            "message": "Testing web dashboard API log creation",
            "category": "Daily Notes & Diary",
            "auto_push": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test_web_session"
    assert "filepath" in data
