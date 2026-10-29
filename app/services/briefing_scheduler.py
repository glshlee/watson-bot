import asyncio
import logging
import os
from typing import Any

from app.config import get_now
from app.db.database import SessionLocal
from app.services.briefing_service import BriefingService
from app.services.supervisor_service import SupervisorService
from app.services.telegram_service import TelegramService

logger = logging.getLogger("watson.briefing_scheduler")


class BriefingScheduler:
    """
    왓슨 텔레그램 정기 브리핑 및 야간 자동 Git 백업 스케줄러 (ADR-026, ADR-064).
    
    한국 표준시(KST)를 기준으로 매일:
    - 🌅 아침 08:30 KST: 오늘의 집중 우선순위 Top 3 및 일정 아침 브리핑 자동 발송
    - 🌇 저녁 20:00 KST: 오늘 완료 하이라이트 요약 및 미완료 과제 이월(Rollover) 저녁 회고 자동 발송
    - 🌙 야간 23:30 KST: 하루 동안 로컬에 축적된 미커밋 라이프로그/GTD 변경분 일괄 커밋 및 원격 자동 푸시 (ADR-064)
    
    수신 대상: settings.TELEGRAM_ALLOWED_CHAT_IDS 에 등록된 모든 사용자.
    """

    def __init__(
        self,
        telegram_service: TelegramService | None = None,
        check_interval_seconds: int = 20,
        nightly_push_time: str | None = None,
    ):
        self.telegram_service = telegram_service or TelegramService()
        self.check_interval_seconds = check_interval_seconds
        self.nightly_push_time: str = nightly_push_time or os.getenv("NIGHTLY_PUSH_TIME", "23:30") or "23:30"
        self.is_running = False

        self.last_dispatched: dict[str, str | None] = {
            "morning": None,
            "evening": None,
            "weekly": None,
            "nightly_push": None,
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
            "weekly_time": "매주 일요일 21:00 KST",
            "nightly_push_time": f"{self.nightly_push_time} KST",
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
            f"⏰ BriefingScheduler started. Monitoring Morning (08:30 KST), Evening (20:00 KST), "
            f"and Nightly Git Auto-Push ({self.nightly_push_time} KST). "
            f"Allowed recipients: {self.telegram_service.allowed_chat_ids}"
        )

        while self.is_running:
            try:
                now = get_now()
                today_str = now.strftime("%Y-%m-%d")

                nhour, nmin = 23, 30
                try:
                    nhour, nmin = map(int, self.nightly_push_time.split(":"))
                except ValueError:
                    nhour, nmin = 23, 30

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

                # 📊 Weekly Review Check: Sunday 21:00 KST (ADR-043)
                elif now.weekday() == 6 and now.hour == 21 and now.minute == 0 and self.last_dispatched.get("weekly") != today_str:
                    logger.info(f"📊 Time matched Sunday 21:00 KST. Dispatching Weekly Review for {today_str}...")
                    self.last_dispatched["weekly"] = today_str
                    asyncio.create_task(self.dispatch_weekly_review())

                # 🌙 Nightly Auto-Commit & Push Check: 23:30 KST (ADR-064)
                elif now.hour == nhour and now.minute == nmin and self.last_dispatched.get("nightly_push") != today_str:
                    logger.info(
                        f"🌙 Time matched {self.nightly_push_time} KST. Running Nightly Git Batch Commit & Auto-Push for {today_str}..."
                    )
                    self.last_dispatched["nightly_push"] = today_str
                    asyncio.create_task(self.dispatch_nightly_git_sync())

                # 🚌 Commute Briefing Check: commute_cfg['send_time'] KST (ADR-030)
                else:

                    try:
                        from app.services.commute_config_service import (
                            CommuteConfigService,
                        )
                        commute_cfg = CommuteConfigService().get_config()
                        if commute_cfg.get("enabled") and self.last_dispatched.get("commute") != today_str:
                            is_weekend = now.weekday() >= 5
                            if not (commute_cfg.get("weekdays_only") and is_weekend):
                                send_time_str = commute_cfg.get("send_time", "07:30")
                                shour, smin = map(int, send_time_str.split(":"))
                                if now.hour == shour and now.minute == smin:
                                    logger.info(f"🚌 Time matched {send_time_str} KST. Dispatching Commute Briefing for {today_str}...")
                                    self.last_dispatched["commute"] = today_str
                                    asyncio.create_task(self.dispatch_commute_briefing())
                    except Exception as ce:  # noqa: BLE001
                        logger.debug(f"Commute briefing schedule check skipped: {ce}")

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

    async def dispatch_weekly_review(
        self,
        target_chat_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        주간 결산 리포트를 생성하여 허용된 텔레그램 사용자들에게 능동 푸시 발송합니다 (ADR-043).
        매주 일요일 21:00 KST 또는 수동 트리거 시 동작합니다.
        """
        recipients = target_chat_ids or self.telegram_service.allowed_chat_ids
        if not self.telegram_service.is_configured():
            logger.warning("Telegram Bot Token is not configured. Skipping weekly review dispatch.")
            return {
                "status": "skipped",
                "reason": "telegram_not_configured",
                "sent_count": 0,
                "recipients": [],
            }

        if not recipients:
            logger.warning("No allowed Telegram Chat IDs configured. Skipping weekly review dispatch.")
            return {
                "status": "skipped",
                "reason": "no_recipients",
                "sent_count": 0,
                "recipients": [],
            }

        db = SessionLocal()
        try:
            supervisor = SupervisorService(db=db)

            # 원격 Git 저장소 최신화 시도 (ADR-009)
            try:
                supervisor.git_service.pull()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Git pull before weekly review dispatch failed (continuing): {e}")

            from app.services.weekly_review_service import WeeklyReviewService

            weekly_service = WeeklyReviewService(
                base_dir=supervisor.base_dir,
                llm_provider=supervisor.llm_provider,
            )
            weekly_data = weekly_service.generate_weekly_review()
            raw_markdown = weekly_data.get("markdown", "")

            header_badge = "📊 **[왓슨 정기 주간 결산 리포트 (일요일 21:00 KST)]**"
            message_text = f"{header_badge}\n\n{raw_markdown}"

            # 인라인 액션 키보드
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "📥 Inbox 정리하기", "callback_data": "action_show_next"},
                        {"text": "⏳ D-Day 확인", "callback_data": "action_show_dday"},
                    ],
                    [
                        {"text": "🔄 원격 최신화", "callback_data": "action_sync"},
                        {"text": "🚀 푸시", "callback_data": "action_push"},
                    ],
                ]
            }

            sent_count = 0
            successful_recipients: list[str] = []

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
                        session_id = f"telegram:{cid}"
                        supervisor.session_service.get_or_create_session(session_id=session_id, channel="telegram")
                        supervisor.session_service.add_message(
                            session_id=session_id,
                            role="assistant",
                            content=message_text,
                        )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to send weekly review to chat_id={cid}: {e}")

            logger.info(
                f"✅ Dispatched weekly review to {sent_count}/{len(recipients)} recipients."
            )
            return {
                "status": "success",
                "mode": "weekly",
                "sent_count": sent_count,
                "recipients": successful_recipients,
                "timestamp": get_now().isoformat(),
            }
        finally:
            db.close()

    async def dispatch_commute_briefing(
        self,
        target_chat_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        출근길 맞춤형 날씨 및 버스 브리핑을 생성하여 허용된 텔레그램 사용자들에게 능동 푸시 발송합니다 (ADR-030).
        """
        recipients = target_chat_ids or self.telegram_service.allowed_chat_ids
        if not self.telegram_service.is_configured():
            logger.warning("Telegram Bot Token is not configured. Skipping commute briefing dispatch.")
            return {
                "status": "skipped",
                "reason": "telegram_not_configured",
                "sent_count": 0,
                "recipients": [],
            }

        if not recipients:
            logger.warning("No allowed Telegram Chat IDs configured. Skipping commute briefing dispatch.")
            return {
                "status": "skipped",
                "reason": "no_recipients",
                "sent_count": 0,
                "recipients": [],
            }

        from app.services.commute_config_service import CommuteConfigService
        service = CommuteConfigService()
        raw_markdown = service.get_standalone_bus_card(force_refresh=True)

        sent_count = 0
        successful_recipients: list[str] = []
        db = SessionLocal()
        try:
            supervisor = SupervisorService(db=db)
            for cid in recipients:
                try:
                    sent = await self.telegram_service.send_message(
                        chat_id=cid,
                        text=raw_markdown,
                        parse_mode="Markdown",
                    )
                    if sent:
                        sent_count += 1
                        successful_recipients.append(str(cid))
                        session_id = f"telegram:{cid}"
                        supervisor.session_service.get_or_create_session(session_id=session_id, channel="telegram")
                        supervisor.session_service.add_message(
                            session_id=session_id,
                            role="assistant",
                            content=raw_markdown,
                        )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to send commute briefing to chat_id={cid}: {e}")

            logger.info(
                f"✅ Dispatched commute briefing to {sent_count}/{len(recipients)} recipients."
            )
            return {
                "status": "success",
                "mode": "commute",
                "sent_count": sent_count,
                "recipients": successful_recipients,
                "timestamp": get_now().isoformat(),
            }
        finally:
            db.close()

    async def dispatch_nightly_git_sync(
        self,
        target_chat_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        매일 밤 지정 시각(기본 23:30 KST)에 GTD 저장소의 미커밋 로컬 작업(is_dirty)과
        미푸시 커밋(ahead_count)을 검사하여 일괄 커밋 및 원격 GitHub 자동 푸시를 수행합니다 (ADR-064).
        변경사항이 없는 경우에는 불필요한 커밋/알림 없이 조용히 스킵합니다.
        """
        db = SessionLocal()
        try:
            supervisor = SupervisorService(db=db)
            git_service = supervisor.git_service
            if not git_service.is_git_repo:
                return {
                    "status": "skipped",
                    "reason": "not_git_repo",
                    "committed": False,
                    "pushed": False,
                    "dirty_files": [],
                    "sent_count": 0,
                }

            dirty_files = git_service.get_dirty_files()
            remote_info = git_service.get_remote_info()
            ahead_count = int(remote_info.get("ahead_count", 0))

            if not dirty_files and ahead_count == 0:
                logger.info("🌙 Nightly Git Sync: Working tree clean and 0 commits ahead. Skipping.")
                return {
                    "status": "skipped",
                    "reason": "no_changes",
                    "committed": False,
                    "pushed": False,
                    "dirty_files": [],
                    "sent_count": 0,
                }

            commit_msg = git_service.build_batch_commit_message(
                dirty_files=dirty_files,
                prefix="docs(auto-backup)",
            )
            pushed, push_msg = git_service.push(
                auto_commit_dirty=True,
                commit_message=commit_msg,
            )

            sent_count = 0
            successful_recipients: list[str] = []
            recipients = target_chat_ids or self.telegram_service.allowed_chat_ids

            if pushed and self.telegram_service.is_configured() and recipients:
                files_str = ", ".join(f"`{os.path.basename(f)}`" for f in dirty_files[:5])
                files_line = f"• **일괄 커밋 파일 ({len(dirty_files)}건)**: {files_str}\n" if dirty_files else ""
                notify_text = (
                    f"🌙 **[왓슨 야간 자동 백업 완료 ({self.nightly_push_time} KST)]**\n\n"
                    f"오늘 하루 로컬에 기록된 라이프로그 및 GTD 변경사항을 모아서 GitHub 원격 저장소에 안전하게 일괄 백업(Commit & Push)했습니다.\n\n"
                    f"{files_line}"
                    f"• **결과**: {push_msg}"
                )
                for cid in recipients:
                    try:
                        sent = await self.telegram_service.send_message(
                            chat_id=cid,
                            text=notify_text,
                            parse_mode="Markdown",
                        )
                        if sent:
                            sent_count += 1
                            successful_recipients.append(str(cid))
                            session_id = f"telegram:{cid}"
                            supervisor.session_service.get_or_create_session(session_id=session_id, channel="telegram")
                            supervisor.session_service.add_message(
                                session_id=session_id,
                                role="assistant",
                                content=notify_text,
                            )
                    except Exception as e:  # noqa: BLE001
                        logger.error(f"Failed to send nightly backup notification to chat_id={cid}: {e}")

            return {
                "status": "success" if pushed else "error",
                "mode": "nightly_push",
                "committed": bool(dirty_files),
                "pushed": pushed,
                "dirty_files": dirty_files,
                "message": push_msg,
                "sent_count": sent_count,
                "recipients": successful_recipients,
                "timestamp": get_now().isoformat(),
            }
        finally:
            db.close()

