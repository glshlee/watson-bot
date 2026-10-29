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
    assert status["nightly_push_time"] == "23:30 KST"
    assert status["telegram_configured"] is True
    assert status["recipients_count"] == 2
    assert "8023809363" in status["recipients"]



@pytest.mark.anyio
async def test_dispatch_briefing_morning(mock_telegram_service, tmp_path):
    scheduler = BriefingScheduler(telegram_service=mock_telegram_service)

    with patch("app.services.briefing_scheduler.SessionLocal") as mock_session_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        mock_weather = {
            "temp": "18.5°C",
            "feels_like": "17.0°C",
            "sky": "맑음 ☀️",
            "rain_prob": "10%",
            "umbrella_tip": "우산 불필요 ☀️",
            "pm10": "좋음 🟢 (25 µg/m³)",
            "pm25": "좋음 🟢 (12 µg/m³)",
            "source": "Open-Meteo API",
            "updated_time": "14:00",
            "is_live": True,
        }
        with patch("app.services.weather_service.WeatherService._fetch_open_meteo", return_value=mock_weather), \
             patch("app.services.briefing_scheduler.SupervisorService") as mock_sup_cls:
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


@pytest.mark.anyio
async def test_dispatch_nightly_git_sync(mock_telegram_service, tmp_path):
    """ADR-064: 야간 자동 백업(23:30 KST) 일괄 커밋·푸시 및 무변경 시 스킵 동작 검증."""
    scheduler = BriefingScheduler(telegram_service=mock_telegram_service)

    with patch("app.services.briefing_scheduler.SessionLocal") as mock_session_cls, \
         patch("app.services.briefing_scheduler.SupervisorService") as mock_sup_cls:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        mock_sup = MagicMock()
        mock_git = MagicMock()
        mock_git.is_git_repo = True

        # 1. 변경사항 없을 때 -> skipped (no_changes)
        mock_git.get_dirty_files.return_value = []
        mock_git.get_remote_info.return_value = {"ahead_count": 0}
        mock_sup.git_service = mock_git
        mock_sup_cls.return_value = mock_sup

        res_skip = await scheduler.dispatch_nightly_git_sync()
        assert res_skip["status"] == "skipped"
        assert res_skip["reason"] == "no_changes"
        assert res_skip["pushed"] is False

        # 2. 미커밋 로컬 파일이 존재할 때 -> 자동 일괄 커밋 + 푸시 + 텔레그램 알림
        mock_git.get_dirty_files.return_value = ["logs/daily/2026-10-27.md", "gtd/inbox.md"]
        mock_git.get_remote_info.return_value = {"ahead_count": 0}
        mock_git.build_batch_commit_message.return_value = "docs(auto-backup): batch update 2 file(s)"
        mock_git.push.return_value = (True, "원격 저장소(`origin/main`)로 1개의 로컬 커밋을 성공적으로 푸시했습니다!")

        res_push = await scheduler.dispatch_nightly_git_sync()
        assert res_push["status"] == "success"
        assert res_push["committed"] is True
        assert res_push["pushed"] is True
        assert res_push["sent_count"] == 2
        mock_git.push.assert_called_once_with(
            auto_commit_dirty=True,
            commit_message="docs(auto-backup): batch update 2 file(s)",
        )

