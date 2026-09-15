import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.services.agent_service import AgentService
from app.services.telegram_service import TelegramService


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


@pytest.mark.anyio
async def test_telegram_authorization():
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = ["1111", "2222"]

    assert service.is_user_authorized("1111") is True
    assert service.is_user_authorized("3333") is False

    # 화이트리스트가 비어있으면 전체 허용
    service.allowed_chat_ids = []
    assert service.is_user_authorized("3333") is True


@pytest.mark.anyio
async def test_telegram_command_start(db_session):
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = []

    update = {
        "update_id": 1,
        "message": {
            "chat": {"id": 12345},
            "text": "/start",
        },
    }

    with patch.object(service, "send_message", new_callable=AsyncMock) as mock_send:
        await service.process_update(update, db_session)
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert args[0] == 12345
        assert "왓슨(Watson)" in args[1]


@pytest.mark.anyio
async def test_telegram_text_workflow_suggestion(db_session):
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = []

    # 운동 일과 메시지 -> log_suggest 인라인 키보드 부착 검증
    update = {
        "update_id": 2,
        "message": {
            "chat": {"id": 12345},
            "text": "오늘 헬스장에서 스쿼트 100kg 완료!",
        },
    }

    with patch.object(service, "send_message", new_callable=AsyncMock) as mock_send:
        await service.process_update(update, db_session)
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        assert "reply_markup" in kwargs
        assert "inline_keyboard" in kwargs["reply_markup"]


@pytest.mark.anyio
async def test_telegram_callback_confirm(db_session, tmp_path):
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = []

    # 먼저 제안 보류 상태 생성
    from app.services.session_service import SessionService
    session_service = SessionService(db_session)
    session_service.set_pending_log("telegram:12345", content="스쿼트 100kg", category="Workout & Health")

    callback_update = {
        "update_id": 3,
        "callback_query": {
            "id": "cb_123",
            "from": {"id": 12345},
            "data": "confirm_log",
        },
    }

    with (
        patch("app.services.settings_service.SettingsService.get_gtd_path", return_value=str(tmp_path)),
        patch("app.services.git_service.GitService.sync_and_commit_push", return_value=True),
        patch.object(service, "answer_callback_query", new_callable=AsyncMock) as mock_ans,
        patch.object(service, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        await service.process_update(callback_update, db_session)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        # 보류가 비워졌는지 확인
        assert session_service.get_pending_log("telegram:12345") is None


@pytest.mark.anyio
async def test_telegram_photo_message(db_session, tmp_path):
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = []

    photo_update = {
        "update_id": 4,
        "message": {
            "chat": {"id": 12345},
            "caption": "오늘의 점심 샐러드",
            "photo": [
                {"file_id": "small_id", "file_size": 100},
                {"file_id": "large_id", "file_size": 2000},
            ],
        },
    }

    with (
        patch("app.services.settings_service.SettingsService.get_gtd_path", return_value=str(tmp_path)),
        patch.object(service, "download_file", new_callable=AsyncMock) as mock_dl,
        patch("app.services.git_service.GitService.sync_and_commit_push", return_value=True),
        patch.object(service, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        mock_dl.return_value = "lifelogs/attachments/mock_salad.jpg"
        await service.process_update(photo_update, db_session)
        mock_dl.assert_called_once()
        dl_args, _ = mock_dl.call_args
        assert dl_args[0] == "large_id"
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert "사진" in args[1]


def test_telegram_briefing_keyboards():
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    morning_kb = service.get_briefing_keyboard(mode="morning")
    assert "inline_keyboard" in morning_kb
    buttons = [btn["callback_data"] for row in morning_kb["inline_keyboard"] for btn in row]
    assert "task_done_top1" in buttons
    assert "action_sync" in buttons
    assert "action_show_tasks" in buttons
    assert "action_push" in buttons

    evening_kb = service.get_briefing_keyboard(mode="evening")
    assert "inline_keyboard" in evening_kb
    evening_buttons = [btn["callback_data"] for row in evening_kb["inline_keyboard"] for btn in row]
    assert "action_prompt_diary" in evening_buttons
    assert "action_sync" in evening_buttons
    assert "action_push" in evening_buttons
    assert "action_show_next" in evening_buttons


@pytest.mark.anyio
async def test_telegram_callback_task_done_top1(db_session, tmp_path):
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = []

    # GTD next_actions.md 파일 생성
    gtd_dir = tmp_path / "gtd"
    gtd_dir.mkdir(parents=True, exist_ok=True)
    next_file = gtd_dir / "next_actions.md"
    next_file.write_text("# Next Actions\n- [ ] 텔레그램 1순위 테스트 태스크\n", encoding="utf-8")

    callback_update = {
        "update_id": 10,
        "callback_query": {
            "id": "cb_top1",
            "from": {"id": 12345},
            "data": "task_done_top1",
        },
    }

    with (
        patch("app.services.settings_service.SettingsService.get_gtd_path", return_value=str(tmp_path)),
        patch("app.services.git_service.GitService.commit", return_value=(True, "commit ok")),
        patch("app.services.git_service.GitService.push", return_value=(True, "push ok")),
        patch.object(service, "answer_callback_query", new_callable=AsyncMock) as mock_ans,
        patch.object(service, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        await service.process_update(callback_update, db_session)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][1]
        assert "1순위 태스크 완료" in sent_text
        assert "텔레그램 1순위 테스트 태스크" in sent_text

    # ADR-032: 스킬 규칙에 따라 GTD 파일에서 잘라내어 제거(Cut)되고, 당일 데일리 로그로 이관(Paste)되었는지 확인
    updated_content = next_file.read_text(encoding="utf-8")
    assert "텔레그램 1순위 테스트 태스크" not in updated_content

    agent_svc = AgentService(base_dir=str(tmp_path))
    daily_log_path = agent_svc.get_lifelog_filepath()
    assert os.path.exists(daily_log_path)
    from pathlib import Path
    daily_content = Path(daily_log_path).read_text(encoding="utf-8")
    assert "- [x] 텔레그램 1순위 테스트 태스크" in daily_content
    assert "## ✅ 오늘 완료한 일 (Completed GTD Tasks)" in daily_content


@pytest.mark.anyio
async def test_telegram_callback_action_sync_and_push(db_session, tmp_path):
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = []

    # 1. action_sync callback
    sync_update = {
        "update_id": 11,
        "callback_query": {
            "id": "cb_sync",
            "from": {"id": 12345},
            "data": "action_sync",
        },
    }

    with (
        patch("app.services.settings_service.SettingsService.get_gtd_path", return_value=str(tmp_path)),
        patch("app.services.git_service.GitService.pull", return_value=(True, "pull ok")),
        patch.object(service, "answer_callback_query", new_callable=AsyncMock) as mock_ans,
        patch.object(service, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        await service.process_update(sync_update, db_session)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        assert "동기화" in mock_send.call_args[0][1]

    # 2. action_push callback
    push_update = {
        "update_id": 12,
        "callback_query": {
            "id": "cb_push",
            "from": {"id": 12345},
            "data": "action_push",
        },
    }

    with (
        patch("app.services.settings_service.SettingsService.get_gtd_path", return_value=str(tmp_path)),
        patch("app.services.git_service.GitService.push", return_value=(True, "push ok")),
        patch.object(service, "answer_callback_query", new_callable=AsyncMock) as mock_ans,
        patch.object(service, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        await service.process_update(push_update, db_session)
        mock_ans.assert_called_once()
        mock_send.assert_called_once()
        assert "푸시" in mock_send.call_args[0][1]


@pytest.mark.anyio
async def test_telegram_command_url(db_session, tmp_path):
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = []

    update = {
        "update_id": 13,
        "message": {
            "chat": {"id": 12345},
            "text": "/url",
        },
    }

    with (
        patch.object(service, "_get_tunnel_url", return_value="https://test-tunnel.trycloudflare.com"),
        patch.object(service, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        await service.process_update(update, db_session)
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert "https://test-tunnel.trycloudflare.com" in args[1]


def test_telegram_bus_keyboard():
    """실시간 버스 인라인 키보드 생성 검증 (ADR-039)."""
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    kb = service.get_bus_keyboard()
    assert "inline_keyboard" in kb
    buttons = [btn["callback_data"] for row in kb["inline_keyboard"] for btn in row]
    assert "action_refresh_bus" in buttons
    assert "action_push" in buttons

    morning_kb = service.get_briefing_keyboard(mode="morning")
    morning_buttons = [btn["callback_data"] for row in morning_kb["inline_keyboard"] for btn in row]
    assert "action_refresh_bus" in morning_buttons


@pytest.mark.anyio
async def test_telegram_callback_action_refresh_bus(db_session):
    """실시간 버스 도착 정보 인라인 새로고침 콜백 검증 (ADR-039)."""
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = []

    refresh_update = {
        "update_id": 20,
        "callback_query": {
            "id": "cb_bus_refresh",
            "from": {"id": 12345},
            "message": {
                "message_id": 999,
                "text": "🚌 **[실시간 출근 버스 도착 정보]** (이전 버스 정보)",
            },
            "data": "action_refresh_bus",
        },
    }

    with (
        patch.object(service, "answer_callback_query", new_callable=AsyncMock) as mock_ans,
        patch.object(service, "edit_message_text", new_callable=AsyncMock, return_value=True) as mock_edit,
    ):
        await service.process_update(refresh_update, db_session)
        mock_ans.assert_called_once()
        mock_edit.assert_called_once()
        kwargs = mock_edit.call_args.kwargs
        assert kwargs["chat_id"] == 12345
        assert kwargs["message_id"] == 999
        assert "[실시간 출근 버스 도착 정보]" in kwargs["text"]


@pytest.mark.anyio
async def test_set_my_commands_success():
    """텔레그램 봇 메뉴 명령어 등록 성공 검증 (ADR-040)."""
    import httpx

    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    
    mock_response = httpx.Response(200, json={"ok": True, "result": True}, request=httpx.Request("POST", "http://test"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        res = await service.set_my_commands()
        assert res is True
        assert mock_post.call_count == 2  # setMyCommands + setChatMenuButton


@pytest.mark.anyio
async def test_set_my_commands_unconfigured():
    """토큰 미설정 시 명령어 등록 건너뛰기 검증 (ADR-040)."""
    service = TelegramService(token="")
    res = await service.set_my_commands()
    assert res is False


@pytest.mark.anyio
async def test_get_my_commands_success():
    """등록된 봇 명령어 목록 조회 검증 (ADR-040)."""
    import httpx

    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    sample_cmds = [
        {"command": "today", "description": "오늘 작성된 일일 로그 확인"},
        {"command": "bus", "description": "실시간 출근 버스 도착 현황 및 갱신"},
    ]
    mock_response = httpx.Response(200, json={"ok": True, "result": sample_cmds}, request=httpx.Request("GET", "http://test"))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        cmds = await service.get_my_commands()
        assert len(cmds) == 2
        assert cmds[0]["command"] == "today"


def test_telegram_commands_endpoints():
    """텔레그램 메뉴 명령어 API 엔드포인트 검증 (ADR-040)."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    # GET /api/telegram/commands
    with patch.object(TelegramService, "get_my_commands", new_callable=AsyncMock, return_value=TelegramService.DEFAULT_COMMANDS):
        res = client.get("/api/telegram/commands")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == len(TelegramService.DEFAULT_COMMANDS)
        assert any(c["command"] == "today" for c in data["commands"])
        assert any(c["command"] == "bus" for c in data["commands"])

    # POST /api/telegram/setup-commands
    with patch.object(TelegramService, "set_my_commands", new_callable=AsyncMock, return_value=True):
        post_res = client.post("/api/telegram/setup-commands")
        assert post_res.status_code == 200
        post_data = post_res.json()
        assert post_data["status"] == "ok"
        assert post_data["commands_count"] == len(TelegramService.DEFAULT_COMMANDS)

    # POST /api/telegram/commands (ADR-041)
    with patch.object(TelegramService, "set_my_commands", new_callable=AsyncMock, return_value=True):
        update_payload = {
            "commands": [
                {"command": "today", "description": "오늘 일일 로그 확인", "enabled": True},
                {"command": "bus", "description": "출근 버스 정보", "enabled": False},
            ],
            "sync_to_telegram": True,
        }
        update_res = client.post("/api/telegram/commands", json=update_payload)
        assert update_res.status_code == 200
        update_data = update_res.json()
        assert update_data["status"] == "ok"
        assert update_data["saved_count"] == 2
        assert update_data["active_count"] == 1
        assert update_data["synced"] is True

    # POST /api/telegram/commands/reset (ADR-041)
    with patch.object(TelegramService, "set_my_commands", new_callable=AsyncMock, return_value=True):
        reset_res = client.post("/api/telegram/commands/reset")
        assert reset_res.status_code == 200
        reset_data = reset_res.json()
        assert reset_data["status"] == "ok"
        assert reset_data["reset_count"] == len(TelegramService.DEFAULT_COMMANDS)






