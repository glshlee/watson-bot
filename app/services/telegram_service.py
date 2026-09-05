import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionLocal
from app.services.agent_service import AgentService
from app.services.git_service import GitService
from app.services.supervisor_service import SupervisorService

logger = logging.getLogger("watson.telegram")


class TelegramService:
    """
    왓슨 텔레그램 봇 연동 서비스 (ADR-006 준수).
    롱 폴링(Long Polling) 및 웹훅을 모두 지원하며,
    화이트리스트 보안, 대화/일과 제안 분리, 인라인 키보드 승인, 사진 기록을 처리합니다.
    """

    def __init__(self, token: str | None = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.allowed_chat_ids = [
            cid.strip() for cid in settings.TELEGRAM_ALLOWED_CHAT_IDS.split(",") if cid.strip()
        ]
        self._is_polling = False

    def is_configured(self) -> bool:
        """텔레그램 봇 토큰이 유효하게 설정되어 있는지 확인합니다."""
        return bool(self.token and len(self.token) > 10)

    def is_user_authorized(self, chat_id: int | str) -> bool:
        """사용자가 허용된 화이트리스트에 속해 있는지 검증합니다."""
        if not self.allowed_chat_ids:
            # 화이트리스트가 비어있으면 모든 사용자 허용 (기본 모드)
            return True
        return str(chat_id) in self.allowed_chat_ids

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str | None = None,
    ) -> bool:
        """텔레그램 사용자에게 메시지를 전송합니다."""
        if not self.is_configured():
            return False

        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.base_url}/sendMessage", json=payload)
                return res.status_code == 200
        except httpx.HTTPError as e:
            logger.error(f"Failed to send telegram message: {e}")
            return False

    async def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> bool:
        """인라인 버튼 클릭에 대한 텔레그램 콜백 응답을 보냅니다."""
        if not self.is_configured():
            return False

        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{self.base_url}/answerCallbackQuery", json=payload)
                return res.status_code == 200
        except httpx.HTTPError as e:
            logger.error(f"Failed to answer callback query: {e}")
            return False

    async def download_file(self, file_id: str, dest_path: str) -> bool:
        """텔레그램 서버에서 파일을 다운로드하여 로컬에 저장합니다."""
        if not self.is_configured():
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{self.base_url}/getFile", params={"file_id": file_id})
                if res.status_code != 200:
                    return False
                file_path = res.json().get("result", {}).get("file_path")
                if not file_path:
                    return False

                download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                file_res = await client.get(download_url)
                if file_res.status_code == 200:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:  # noqa: ASYNC230
                        f.write(file_res.content)
                    return True
        except (httpx.HTTPError, OSError) as e:
            logger.error(f"Failed to download telegram file: {e}")
        return False

    async def process_update(self, update: dict[str, Any], db: Session) -> None:
        """텔레그램 Update 객체(메시지, 콜백 등)를 분석하고 처리합니다."""
        # 1. 인라인 키보드 콜백 쿼리 (Callback Query) 처리
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb["id"]
            from_user = cb["from"]
            chat_id = from_user["id"]
            data = cb.get("data", "")

            if not self.is_user_authorized(chat_id):
                await self.answer_callback_query(cb_id, text="접근 권한이 없습니다.")
                return

            supervisor = SupervisorService(db=db)
            session_id = f"telegram:{chat_id}"

            if data == "confirm_log":
                await self.answer_callback_query(cb_id, text="기록을 저장합니다...")
                result = supervisor.process_user_request(
                    session_id=session_id,
                    user_message="응 좋아 기록해줘",
                    channel="telegram",
                    auto_push=True,
                )
                await self.send_message(chat_id, result["ai_response"])
            elif data == "reject_log":
                await self.answer_callback_query(cb_id, text="기록을 취소했습니다.")
                result = supervisor.process_user_request(
                    session_id=session_id,
                    user_message="아니 괜찮아",
                    channel="telegram",
                    auto_push=False,
                )
                await self.send_message(chat_id, result["ai_response"])
            return

        # 2. 일반 메시지 처리
        msg = update.get("message")
        if not msg:
            return

        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id:
            return

        # 화이트리스트 검증
        if not self.is_user_authorized(chat_id):
            await self.send_message(
                chat_id,
                f"🔒 죄송합니다. 이 봇은 개인 전용 AI 비서입니다.\n당신의 Chat ID: `{chat_id}`\n관리자에게 문의해 주세요.",
            )
            return

        text = msg.get("text", "").strip()

        # 2-1. 명령어 처리
        if text.startswith("/start"):
            welcome_text = (
                "👋 안녕하세요! 24시간 개인 라이프로그 AI 비서 **왓슨(Watson)**입니다.\n\n"
                "일상 대화부터 질문, 그리고 오늘 일어난 일이나 운동, 생각을 편하게 말씀해 주세요.\n"
                "의미 있는 일과는 비서가 알아서 캐치해 마크다운 일기로 남겨드려요!\n\n"
                f"📌 사용자 Chat ID: `{chat_id}`\n"
                "💡 명령어 안내:\n"
                "• `/log [내용]`: 즉시 오늘 라이프로그에 기록\n"
                "• `/status`: 서버 및 깃허브 연동 상태 확인\n"
                "• `/help`: 도움말 확인"
            )
            await self.send_message(chat_id, welcome_text)
            return

        if text.startswith("/help"):
            help_text = (
                "📖 **Watson 텔레그램 봇 사용법**\n\n"
                "1. **자유로운 대화**: '오늘 날씨 어때?', '1부터 30 중에 골라줘' 등 무엇이든 물어보세요.\n"
                "2. **일과 공유 & 자동 제안**: '오늘 헬스장 다녀옴', '프로젝트 킥오프 완료' 등 일과를 말하면 비서가 기록할지 여부를 버튼으로 여쭤봅니다.\n"
                "3. **사진 전송**: 일상 사진이나 영수증을 보내면 오늘 라이프로그에 사진이 첨부됩니다.\n"
                "4. **직접 기록**: `/log 러닝 5km 완료` 명령어로 바로 기록할 수 있습니다."
            )
            await self.send_message(chat_id, help_text)
            return

        if text.startswith("/status"):
            git_service = GitService(repo_path=".")
            status_text = (
                "🤖 **Watson Agent 시스템 상태**\n\n"
                f"• 서버 상태: 정상 가동 중 (Online 24/7)\n"
                f"• 세션 ID: `telegram:{chat_id}`\n"
                f"• Git 브랜치: `{settings.GIT_BRANCH}`\n"
                f"• Git 원격 저장소: `{settings.GIT_REMOTE_NAME}`\n"
                f"• 최근 동기화 시간: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
            await self.send_message(chat_id, status_text)
            return

        # 2-2. 사진(Photo) 수신 처리
        if "photo" in msg:
            photos = msg["photo"]
            caption = msg.get("caption", "").strip() or "일상 사진 메모"
            largest_photo = photos[-1]  # 가장 고화질 사진
            file_id = largest_photo["file_id"]

            now = datetime.now(timezone.utc)
            year_str = now.strftime("%Y")
            month_str = now.strftime("%m")
            filename = f"tg_{int(now.timestamp())}_{file_id[:8]}.jpg"
            rel_path = f"static/images/{year_str}/{month_str}/{filename}"
            abs_path = os.path.join(settings.REPO_PATH, "app", rel_path)

            success = await self.download_file(file_id, abs_path)
            if success:
                # 마크다운 라이프로그에 이미지 링크 추가
                agent_service = AgentService(base_dir=settings.REPO_PATH)
                git_service = GitService(repo_path=settings.REPO_PATH)
                img_md = f"![{caption}](/{rel_path})\n  > {caption}"
                filepath = agent_service.append_or_update_lifelog(
                    content=img_md,
                    category="Media & Attachments",
                    date_obj=now,
                )
                commit_msg = f"docs(lifelog): Add photo attachment for {now.strftime('%Y-%m-%d')} [telegram:{chat_id}]"
                git_service.sync_and_commit_push(commit_message=commit_msg, file_path=filepath)

                await self.send_message(
                    chat_id,
                    "📷 소중한 사진과 메모를 오늘 자 라이프로그 **[Media & Attachments]**에 안전하게 보관하고 GitHub에 커밋했습니다! ✨",
                )
            else:
                await self.send_message(chat_id, "⚠️ 사진을 다운로드하는 도중 오류가 발생했습니다.")
            return

        # 2-3. 일반 텍스트 대화 ➔ 지능형 비서 파이프라인 연동
        if text:
            supervisor = SupervisorService(db=db)
            session_id = f"telegram:{chat_id}"

            result = supervisor.process_user_request(
                session_id=session_id,
                user_message=text,
                channel="telegram",
                auto_push=True,
            )

            intent = result.get("intent", "chat_only")
            ai_response = result.get("ai_response", "")

            if intent == "log_suggest":
                # 인라인 키보드 버튼 부착 (원클릭 승인/거절)
                reply_markup = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ 응, 기록해줘", "callback_data": "confirm_log"},
                            {"text": "❌ 아니야", "callback_data": "reject_log"},
                        ]
                    ]
                }
                await self.send_message(chat_id, ai_response, reply_markup=reply_markup)
            else:
                await self.send_message(chat_id, ai_response)

    async def start_polling(self) -> None:
        """텔레그램 롱 폴링(getUpdates) 루프를 시작합니다."""
        if not self.is_configured():
            logger.info("Telegram bot token not configured. Skipping polling.")
            return

        logger.info("🚀 Starting Telegram Bot Long Polling...")
        self._is_polling = True
        offset = 0

        async with httpx.AsyncClient(timeout=35.0) as client:
            while self._is_polling:
                try:
                    params = {"offset": offset, "timeout": 30}
                    res = await client.get(f"{self.base_url}/getUpdates", params=params)
                    if res.status_code == 200:
                        data = res.json()
                        updates = data.get("result", [])
                        for update in updates:
                            update_id = update["update_id"]
                            offset = update_id + 1

                            # 독립 DB 세션에서 업데이트 처리
                            db = SessionLocal()
                            try:
                                await self.process_update(update, db)
                            finally:
                                db.close()
                    elif res.status_code in [401, 404]:
                        logger.error(f"Invalid Telegram bot token: {res.status_code}")
                        self._is_polling = False
                        break
                    else:
                        await asyncio.sleep(2)
                except asyncio.CancelledError:
                    logger.info("Telegram polling cancelled.")
                    self._is_polling = False
                    break
                except (httpx.HTTPError, asyncio.TimeoutError) as e:
                    logger.error(f"Telegram polling error: {e}")
                    await asyncio.sleep(3)

    def stop_polling(self) -> None:
        """폴링 루프를 중단합니다."""
        self._is_polling = False
