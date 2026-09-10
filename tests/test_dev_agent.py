from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.main import app
from app.services.dev_agent_service import DevAgentService

client = TestClient(app)

def test_dev_agent_service_lifecycle():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    service = DevAgentService(db=db)

    # 1. Workspace status
    ws = service.get_workspace_status()
    assert "workspace" in ws
    assert "branch" in ws
    assert "changed_files_count" in ws

    # 2. Process /status
    res_status = service.process_dev_request("dev_test_1", "/status")
    assert res_status["action_type"] == "git_status"
    assert "Git 상태" in res_status["ai_response"]

    # 3. Process /log
    res_log = service.process_dev_request("dev_test_1", "/log")
    assert res_log["action_type"] == "git_log"
    assert "커밋 내역" in res_log["ai_response"]

    # 4. Process general technical query
    res_query = service.process_dev_request("dev_test_1", "이 프로젝트 구조 설명해줘")
    assert res_query["action_type"] == "ai_reasoning"
    assert len(res_query["ai_response"]) > 10

    # 5. Verify sessions saved with agent_type="dev"
    sessions = service.session_service.list_sessions(agent_type="dev")
    assert len(sessions) == 1
    assert sessions[0]["id"] == "dev_test_1"
    assert sessions[0]["agent_type"] == "dev"


def test_hub_and_dev_endpoints():
    # 1. Portal root GET /
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Agent Workspace" in res_root.text

    # 2. Watson console GET /watson
    res_watson = client.get("/watson")
    assert res_watson.status_code == 200
    assert "Watson - 24/7 AI Agent Console" in res_watson.text

    # 3. Dev console GET /dev
    res_dev = client.get("/dev")
    assert res_dev.status_code == 200
    assert "DevBot - Software Engineering Console" in res_dev.text

    # 4. Hub status API GET /api/hub/status
    res_hub = client.get("/api/hub/status")
    assert res_hub.status_code == 200
    hub_data = res_hub.json()
    assert hub_data["total_agents"] == 2
    assert any(a["id"] == "watson" for a in hub_data["agents"])
    assert any(a["id"] == "dev" for a in hub_data["agents"])

    # 5. Dev chat API POST /api/dev/chat
    res_chat = client.post(
        "/api/dev/chat",
        json={"session_id": "test_dev_endpoint_session", "message": "/status"}
    )
    assert res_chat.status_code == 200
    data = res_chat.json()
    assert data["session_id"] == "test_dev_endpoint_session"
    assert "ai_response" in data

    # 6. Dev sessions API GET /api/dev/sessions
    res_dev_sessions = client.get("/api/dev/sessions")
    assert res_dev_sessions.status_code == 200
    assert isinstance(res_dev_sessions.json(), list)

    # 7. Dev status API GET /api/dev/status
    res_dev_status = client.get("/api/dev/status")
    assert res_dev_status.status_code == 200
    assert "branch" in res_dev_status.json()

    # Clean up test session
    client.delete("/api/sessions/test_dev_endpoint_session")


def test_dev_agent_toolchain():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    service = DevAgentService(db=db)

    # 1. /help
    res_help = service.process_dev_request("dev_tool_test", "/help")
    assert res_help["action_type"] == "tool_help"
    assert "/test" in res_help["ai_response"]
    assert "/lint" in res_help["ai_response"]
    assert "/commit" in res_help["ai_response"]

    # 2. /lint
    res_lint = service.process_dev_request("dev_tool_test", "/lint")
    assert res_lint["action_type"] == "tool_lint"
    assert "Ruff" in res_lint["ai_response"]
    assert "Mypy" in res_lint["ai_response"]


    # 3. /commit recommendation
    res_commit_rec = service.process_dev_request("dev_tool_test", "/commit")
    assert res_commit_rec["action_type"] == "tool_commit"
    assert "Conventional Commits" in res_commit_rec["ai_response"]


    # 4. /test targeting specific file
    res_test = service.process_dev_request("dev_tool_test", "/test tests/test_auth.py")
    assert res_test["action_type"] == "tool_test"
    assert "pytest" in res_test["ai_response"]

    # 5. /today shortcut
    res_today = service.process_dev_request("dev_tool_test", "/today")
    assert res_today["action_type"] == "tool_today_log"
    assert "일일 로그" in res_today["ai_response"]

    # 6. /gtd shortcut
    res_gtd = service.process_dev_request("dev_tool_test", "/gtd")
    assert res_gtd["action_type"] == "tool_gtd_files"
    assert "GTD 파일 현황" in res_gtd["ai_response"]

