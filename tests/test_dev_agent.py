import os

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
    assert ("Conventional Commits" in res_commit_rec["ai_response"] or "현재 작업 트리가 깨끗하여" in res_commit_rec["ai_response"])


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

    # 7. /push command (ADR-055)
    res_push = service.process_dev_request("dev_tool_test", "/push")
    assert res_push["action_type"] == "tool_push"
    assert ("GitHub 원격 푸시" in res_push["ai_response"])

    # 8. /sync command (ADR-055)
    res_sync = service.process_dev_request("dev_tool_test", "/sync")
    assert res_sync["action_type"] == "tool_sync"
    assert ("원격 GitHub 동기화" in res_sync["ai_response"])

    # 9. /roadmap command (ADR-057)
    res_roadmap = service.process_dev_request("dev_tool_test", "/roadmap")
    assert res_roadmap["action_type"] == "tool_roadmap"
    assert "개발 로드맵 & 마일스톤 현황" in res_roadmap["ai_response"]
    assert "진척도" in res_roadmap["ai_response"]

    # 10. /skills command (ADR-057)
    res_skills = service.process_dev_request("dev_tool_test", "/skills")
    assert res_skills["action_type"] == "tool_skills"
    assert "하네스 개발 스킬 카탈로그" in res_skills["ai_response"]
    assert "dev-workflow" in res_skills["ai_response"]

    # 11. /skill <name> command (ADR-057)
    res_skill_detail = service.process_dev_request("dev_tool_test", "/skill dev-workflow")
    assert res_skill_detail["action_type"] == "tool_skill_detail"
    assert "개발 스킬 상세" in res_skill_detail["ai_response"]
    assert "dev-workflow" in res_skill_detail["ai_response"]

    res_skill_invalid = service.process_dev_request("dev_tool_test", "/skill nonexistent_xyz")
    assert res_skill_invalid["action_type"] == "tool_skill_detail"
    assert "찾을 수 없습니다" in res_skill_invalid["ai_response"]


def test_dev_roadmap_and_skills_api():
    # 1. GET /api/dev/roadmap
    res_roadmap = client.get("/api/dev/roadmap")
    assert res_roadmap.status_code == 200
    roadmap_data = res_roadmap.json()
    assert "total_phases" in roadmap_data
    assert "completed_phases" in roadmap_data
    assert "completion_rate" in roadmap_data
    assert "progress_bar" in roadmap_data
    assert "markdown" in roadmap_data
    assert roadmap_data["total_phases"] > 0

    # 2. GET /api/dev/skills
    res_skills = client.get("/api/dev/skills")
    assert res_skills.status_code == 200
    skills_data = res_skills.json()
    assert "total_skills" in skills_data
    assert "skills" in skills_data
    assert "markdown" in skills_data
    assert skills_data["total_skills"] >= 4
    assert any(s["id"] == "dev-workflow" for s in skills_data["skills"])

    # 3. GET /api/dev/skills/{skill_name}
    res_detail = client.get("/api/dev/skills/dev-workflow")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["id"] == "dev-workflow"
    assert "content" in detail_data

    # 4. GET /api/dev/skills/nonexistent (404)
    res_404 = client.get("/api/dev/skills/nonexistent_xyz")
    assert res_404.status_code == 404


def test_dev_coding_studio_api_and_commands(tmp_path):
    # 1. Test DevAgentService studio commands
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    service = DevAgentService(db=db)

    # Command: /files
    res_files = service.process_dev_request("dev_studio_test", "/files")
    assert res_files["action_type"] == "tool_files_list"
    assert "파일 탐색기" in res_files["ai_response"]

    # Command: /code
    res_code = service.process_dev_request("dev_studio_test", "/code app/main.py")
    assert res_code["action_type"] == "tool_code_view"
    assert "소스코드 확인" in res_code["ai_response"]

    # Command: /heal (mock or live pytest)
    res_heal = service.process_dev_request("dev_studio_test", "/heal")
    assert res_heal["action_type"] == "tool_self_heal"
    assert "자가 치유" in res_heal["ai_response"]

    # 2. REST API: GET /api/dev/code/tree
    res_tree = client.get("/api/dev/code/tree")
    assert res_tree.status_code == 200
    tree_data = res_tree.json()
    assert "files" in tree_data
    assert tree_data["total_files"] > 0
    assert any("main.py" in f["name"] for f in tree_data["files"])

    # 3. REST API: GET /api/dev/code/file
    res_file = client.get("/api/dev/code/file?filepath=app/main.py&start_line=1&end_line=20")
    assert res_file.status_code == 200
    file_data = res_file.json()
    assert file_data["success"] is True
    assert "app" in file_data["content"]
    assert file_data["language"] == "python"

    # 4. Security Guardrails: Path Traversal (403) & Sensitive files (403) & Not Found (404)
    res_traversal = client.get("/api/dev/code/file?filepath=../../etc/passwd")
    assert res_traversal.status_code == 403

    res_env = client.get("/api/dev/code/file?filepath=.env")
    assert res_env.status_code == 403

    res_404 = client.get("/api/dev/code/file?filepath=nonexistent_file_xyz.py")
    assert res_404.status_code == 404

    # 5. REST API: POST /api/dev/code/patch (dry_run diff preview)
    test_file = tmp_path / "studio_api_test.py"
    test_file.write_text("x = 10\nprint(x)\n", encoding="utf-8")
    rel_tmp = str(test_file.relative_to(tmp_path))

    # Temporarily set workspace_path to tmp_path
    service.coding_studio.workspace_path = str(tmp_path)
    service.coding_studio.backups_dir = str(tmp_path / ".backups")

    diff_res = service.coding_studio.generate_diff_preview(
        rel_tmp,
        target_content="x = 10",
        replacement_content="x = 20",
    )
    assert diff_res["success"] is True
    assert "+x = 20" in diff_res["diff"]

    # Patch live
    patch_res = service.coding_studio.apply_code_patch(
        rel_tmp,
        target_content="x = 10",
        replacement_content="x = 20",
    )
    assert patch_res["success"] is True
    assert test_file.read_text(encoding="utf-8") == "x = 20\nprint(x)\n"

    # 6. REST API: POST /api/dev/code/patch & rollback live endpoint test
    scratch_file = "tests/test_scratch_temp.txt"
    try:
        with open(scratch_file, "w", encoding="utf-8") as sf:
            sf.write("alpha = 1\nbeta = 2\n")

        # dry_run diff
        res_diff_api = client.post(
            "/api/dev/code/patch",
            json={
                "filepath": scratch_file,
                "target_content": "alpha = 1",
                "replacement_content": "alpha = 99",
                "dry_run": True,
            },
        )
        assert res_diff_api.status_code == 200
        assert "+alpha = 99" in res_diff_api.json()["diff"]

        # live patch
        res_patch_api = client.post(
            "/api/dev/code/patch",
            json={
                "filepath": scratch_file,
                "target_content": "alpha = 1",
                "replacement_content": "alpha = 99",
                "dry_run": False,
            },
        )
        assert res_patch_api.status_code == 200
        assert res_patch_api.json()["success"] is True

        # rollback
        res_rollback_api = client.post(
            "/api/dev/code/rollback",
            json={"filepath": scratch_file},
        )
        assert res_rollback_api.status_code == 200
        assert res_rollback_api.json()["success"] is True
    finally:
        if os.path.exists(scratch_file):
            os.remove(scratch_file)

    # 7. REST API: POST /api/dev/code/self-heal
    res_api_heal = client.post("/api/dev/code/self-heal")
    assert res_api_heal.status_code == 200
    heal_data = res_api_heal.json()
    assert "test_passed" in heal_data
    assert "diagnosis" in heal_data


def test_dev_agent_studio_and_autonomous_implementation():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    service = DevAgentService(db=db, fast_mode=True)

    # 1. /studio command
    res_studio = service.process_dev_request("dev_impl_test", "/studio app/services/dev_agent_service.py")
    assert res_studio["action_type"] == "tool_studio_open"
    assert res_studio["target_file"] == "app/services/dev_agent_service.py"
    assert "웹 코딩 스튜디오" in res_studio["ai_response"]

    # 2. /files command contains [편집] and data-open-studio
    res_files = service.process_dev_request("dev_impl_test", "/files")
    assert res_files["action_type"] == "tool_files_list"
    assert "data-open-studio=" in res_files["ai_response"]

    # 3. /implement command in fast mode
    res_impl = service.process_dev_request("dev_impl_test", "/implement app/models/test.py 새 필드 추가해줘")
    assert res_impl["action_type"] == "tool_code_patch"
    assert res_impl["target_file"] == "app/models/test.py"
    assert "자율 코드 구현" in res_impl["ai_response"]

    # 4. Direct pipe patch
    dummy_file = "tests/test_pipe_dummy.txt"
    try:
        with open(dummy_file, "w", encoding="utf-8") as f:
            f.write("hello world\nversion 1.0\n")

        res_pipe = service.process_dev_request(
            "dev_impl_test",
            f"/patch {dummy_file} | version 1.0 | version 2.0",
        )
        assert res_pipe["action_type"] == "tool_code_patch"
        assert res_pipe["target_file"] == dummy_file
        with open(dummy_file, encoding="utf-8") as f:
            content = f.read()
        assert "version 2.0" in content
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)


