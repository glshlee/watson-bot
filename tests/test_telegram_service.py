from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
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

    # 파일 내 체크박스가 - [x] 로 변경되었는지 확인
    updated_content = next_file.read_text(encoding="utf-8")
    assert "- [x] 텔레그램 1순위 테스트 태스크" in updated_content


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



