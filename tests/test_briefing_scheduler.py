from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.briefing_scheduler import BriefingScheduler
from app.services.telegram_service import TelegramService


@pytest.fixture
def mock_telegram_service():
    service = TelegramService(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    service.allowed_chat_ids = ["8023809363", "9999999999"]
    service.send_message = AsyncMock(return_value=True)  # type: ignore[method-assign]
    return service


def test_scheduler_status(mock_telegram_service):
    scheduler = BriefingScheduler(telegram_service=mock_telegram_service)
    status = scheduler.get_scheduler_status()

    assert status["is_running"] is False
    assert status["morning_time"] == "08:30 KST"
    assert status["evening_time"] == "20:00 KST"
    assert status["telegram_configured"] is True
    assert status["recipients_count"] == 2
    assert "8023809363" in status["recipients"]


@pytest.mark.anyio
async def test_dispatch_briefing_morning(mock_telegram_service, tmp_path):
    scheduler = BriefingScheduler(telegram_service=mock_telegram_service)

    with patch("app.services.briefing_scheduler.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        with patch("app.services.briefing_scheduler.SupervisorService") as mock_sup_cls:
            mock_sup = MagicMock()
            mock_sup.base_dir = str(tmp_path)
            mock_sup.git_service = MagicMock()
            mock_sup.llm_provider = MagicMock()
            mock_sup.session_service = MagicMock()
            mock_sup.get_briefing.return_value = {
                "mode": "morning",
                "markdown": "### Watson Morning Briefing\n오늘 집중 우선순위",
            }
            mock_sup_cls.return_value = mock_sup

            result = await scheduler.dispatch_briefing(mode="morning")

            assert result["status"] == "success"
            assert result["mode"] == "morning"
            assert result["sent_count"] == 2
            assert len(result["recipients"]) == 2

            # Verify send_message was called for both recipients
            assert mock_telegram_service.send_message.call_count == 2
            call_args_list = mock_telegram_service.send_message.call_args_list
            assert call_args_list[0].kwargs["chat_id"] == "8023809363"
            assert "왓슨 정기 아침 브리핑" in call_args_list[0].kwargs["text"]
            assert "reply_markup" in call_args_list[0].kwargs
            assert "inline_keyboard" in call_args_list[0].kwargs["reply_markup"]
            assert call_args_list[1].kwargs["chat_id"] == "9999999999"


@pytest.mark.anyio
async def test_dispatch_briefing_unconfigured():
    unconfigured_service = TelegramService(token="")
    unconfigured_service.allowed_chat_ids = []
    scheduler = BriefingScheduler(telegram_service=unconfigured_service)

    result = await scheduler.dispatch_briefing(mode="evening")
    assert result["status"] == "skipped"
    assert result["reason"] == "telegram_not_configured"
    assert result["sent_count"] == 0
