import asyncio
import logging
from typing import Any

from app.config import get_now
from app.db.database import SessionLocal
from app.services.briefing_service import BriefingService
from app.services.supervisor_service import SupervisorService
from app.services.telegram_service import TelegramService

logger = logging.getLogger("watson.briefing_scheduler")


class BriefingScheduler:
    """
    왓슨 텔레그램 정기 브리핑 자동 푸시 스케줄러 (ADR-026).
    
    한국 표준시(KST)를 기준으로 매일:
    - 🌅 아침 08:30 KST: 오늘의 집중 우선순위 Top 3 및 일정 아침 브리핑 자동 발송
    - 🌇 저녁 20:00 KST: 오늘 완료 하이라이트 요약 및 미완료 과제 이월(Rollover) 저녁 회고 자동 발송
    
    수신 대상: settings.TELEGRAM_ALLOWED_CHAT_IDS 에 등록된 모든 사용자.
    """

    def __init__(
        self,
        telegram_service: TelegramService | None = None,
        check_interval_seconds: int = 20,
    ):
        self.telegram_service = telegram_service or TelegramService()
        self.check_interval_seconds = check_interval_seconds
        self.is_running = False
        self.last_dispatched: dict[str, str | None] = {
            "morning": None,
            "evening": None,
        }

    def get_scheduler_status(self) -> dict[str, Any]:
        """스케줄러의 실시간 구동 상태 및 발송 이력을 반환합니다."""
        now = get_now()
        return {
            "is_running": self.is_running,
            "current_time": now.strftime("%H:%M KST"),
            "current_date": now.strftime("%Y-%m-%d"),
            "morning_time": "08:30 KST",
            "evening_time": "20:00 KST",
            "last_dispatched": self.last_dispatched,
            "telegram_configured": self.telegram_service.is_configured(),
            "recipients": self.telegram_service.allowed_chat_ids,
            "recipients_count": len(self.telegram_service.allowed_chat_ids),
        }

    async def start(self) -> None:
        """스케줄러 백그라운드 루프를 시작합니다."""
        if self.is_running:
            logger.warning("BriefingScheduler is already running.")
            return

        self.is_running = True
        logger.info(
            f"⏰ BriefingScheduler started. Monitoring Morning (08:30 KST) and Evening (20:00 KST). "
            f"Allowed recipients: {self.telegram_service.allowed_chat_ids}"
        )

        while self.is_running:
            try:
                now = get_now()
                today_str = now.strftime("%Y-%m-%d")

                # 🌅 Morning Briefing Check: 08:30 KST
                if now.hour == 8 and now.minute == 30 and self.last_dispatched.get("morning") != today_str:
                    logger.info(f"🌅 Time matched 08:30 KST. Dispatching Morning Briefing for {today_str}...")
                    self.last_dispatched["morning"] = today_str
                    asyncio.create_task(self.dispatch_briefing(mode="morning"))

                # 🌇 Evening Briefing Check: 20:00 KST
                elif now.hour == 20 and now.minute == 0 and self.last_dispatched.get("evening") != today_str:
                    logger.info(f"🌇 Time matched 20:00 KST. Dispatching Evening Briefing for {today_str}...")
                    self.last_dispatched["evening"] = today_str
                    asyncio.create_task(self.dispatch_briefing(mode="evening"))

            except Exception:
                logger.exception("Error in BriefingScheduler loop")

            await asyncio.sleep(self.check_interval_seconds)

    def stop(self) -> None:
        """스케줄러 루프를 중지합니다."""
        logger.info("🛑 Stopping BriefingScheduler...")
        self.is_running = False

    async def dispatch_briefing(
        self,
        mode: str = "auto",
        target_chat_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        아침 또는 저녁 브리핑을 생성하여 허용된 텔레그램 사용자들에게 푸시 발송합니다.
        """
        recipients = target_chat_ids or self.telegram_service.allowed_chat_ids
        if not self.telegram_service.is_configured():
            logger.warning("Telegram Bot Token is not configured. Skipping briefing dispatch.")
            return {
                "status": "skipped",
                "reason": "telegram_not_configured",
                "sent_count": 0,
                "recipients": [],
            }

        if not recipients:
            logger.warning("No allowed Telegram Chat IDs configured. Skipping briefing dispatch.")
            return {
                "status": "skipped",
                "reason": "no_recipients",
                "sent_count": 0,
                "recipients": [],
            }

        # 1. 브리핑 생성
        db = SessionLocal()
        try:
            supervisor = SupervisorService(db=db)

            # 원격 Git 저장소 최신화 시도 (ADR-009)
            try:
                supervisor.git_service.pull()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Git pull before briefing dispatch failed (continuing): {e}")

            # 모드 결정
            briefing_service = BriefingService(
                base_dir=supervisor.base_dir,
                llm_provider=supervisor.llm_provider,
                git_service=supervisor.git_service,
            )
            resolved_mode = briefing_service.detect_briefing_mode(override_mode=mode)
            briefing_data = briefing_service.generate_briefing(mode=resolved_mode)
            raw_markdown = briefing_data.get("markdown", "")

            header_badge = (
                "🌅 **[왓슨 정기 아침 브리핑 (08:30 KST)]**"
                if resolved_mode == "morning"
                else "🌇 **[왓슨 정기 저녁 일과 회고 (20:00 KST)]**"
            )
            message_text = f"{header_badge}\n\n{raw_markdown}"

            # 2. 텔레그램 발송 및 세션 히스토리 저장
            sent_count = 0
            successful_recipients: list[str] = []

            reply_markup = self.telegram_service.get_briefing_keyboard(mode=resolved_mode)

            for cid in recipients:
                try:
                    sent = await self.telegram_service.send_message(
                        chat_id=cid,
                        text=message_text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown",
                    )
                    if sent:
                        sent_count += 1
                        successful_recipients.append(str(cid))
                        # 텔레그램 세션 히스토리에 기록 보존 (ADR-002, ADR-010)
                        session_id = f"telegram:{cid}"
                        supervisor.session_service.get_or_create_session(session_id=session_id, channel="telegram")
                        supervisor.session_service.add_message(
                            session_id=session_id,
                            role="assistant",
                            content=message_text,
                        )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to send briefing to chat_id={cid}: {e}")

            logger.info(
                f"✅ Dispatched {resolved_mode} briefing to {sent_count}/{len(recipients)} recipients."
            )
            return {
                "status": "success",
                "mode": resolved_mode,
                "sent_count": sent_count,
                "recipients": successful_recipients,
                "timestamp": get_now().isoformat(),
            }
        finally:
            db.close()
