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
async def test_telegram_callback_confirm(db_session):
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

