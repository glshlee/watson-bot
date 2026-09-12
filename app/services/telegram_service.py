import asyncio
import logging
import os
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_now, settings
from app.db.database import SessionLocal
from app.services.agent_service import AgentService
from app.services.git_service import GitService
from app.services.settings_service import SettingsService
from app.services.supervisor_service import SupervisorService

logger = logging.getLogger("watson.telegram")


class TelegramService:
    """
    왓슨 텔레그램 봇 연동 서비스 (ADR-006 준수).
    롱 폴링(Long Polling) 및 웹훅을 모두 지원하며,
    화이트리스트 보안, 대화/일과 제안 분리, 인라인 키보드 승인, 사진 기록을 처리합니다.
    """

    def __init__(self, token: str | None = None):
        self.token = token if token is not None else settings.TELEGRAM_BOT_TOKEN
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
                if res.status_code != 200 and parse_mode:
                    logger.warning(
                        f"Telegram sendMessage with parse_mode={parse_mode} failed ({res.status_code}: {res.text}), retrying without parse_mode..."
                    )
                    payload.pop("parse_mode", None)
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

    def _get_tunnel_url(self) -> str:
        """현재 활성화된 Cloudflare Tunnel 접속 URL을 조회합니다."""
        url_file = os.path.join(settings.REPO_PATH, "tunnel_url.txt")
        if os.path.exists(url_file):
            try:
                with open(url_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except OSError:
                pass
        return ""

    def get_briefing_keyboard(self, mode: str = "morning") -> dict[str, Any]:
        """
        아침/저녁 브리핑 메시지에 첨부할 인터랙티브 인라인 키보드를 생성합니다 (ADR-027).
        """
        if mode == "morning":
            return {
                "inline_keyboard": [
                    [
                        {"text": "✅ 1순위 태스크 완료", "callback_data": "task_done_top1"},
                        {"text": "🔄 GTD 동기화", "callback_data": "action_sync"},
                    ],
                    [
                        {"text": "📋 전체 할 일 보기", "callback_data": "action_show_tasks"},
                        {"text": "🚀 원격 푸시", "callback_data": "action_push"},
                    ],
                ]
            }
        else:  # evening or general
            return {
                "inline_keyboard": [
                    [
                        {"text": "📝 오늘 일기 작성", "callback_data": "action_prompt_diary"},
                        {"text": "🔄 GTD 동기화", "callback_data": "action_sync"},
                    ],
                    [
                        {"text": "🚀 오늘 기록 푸시", "callback_data": "action_push"},
                        {"text": "📋 내일 할 일 보기", "callback_data": "action_show_next"},
                    ],
                ]
            }

    async def process_update(self, update: dict[str, Any], db: Session) -> None:
        """텔레그램 Update 객체(메시지, 콜백 등)를 분석하고 처리합니다."""
        # 1. 인라인 키보드 콜백 쿼리 (Callback Query) 처리 (ADR-006, ADR-027)
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
            elif data == "task_done_top1":
                await self.answer_callback_query(cb_id, text="1순위 태스크 완료 처리 중...")
                result = supervisor.process_user_request(
                    session_id=session_id,
                    user_message="/done",
                    channel="telegram",
                    auto_push=True,
                )
                await self.send_message(chat_id, result["ai_response"])
            elif data == "action_sync":
                await self.answer_callback_query(cb_id, text="GTD 저장소 동기화 중...")
                result = supervisor.process_user_request(
                    session_id=session_id,
                    user_message="/sync",
                    channel="telegram",
                    auto_push=False,
                )
                await self.send_message(chat_id, result["ai_response"])
            elif data == "action_push":
                await self.answer_callback_query(cb_id, text="GitHub 원격 푸시 중...")
                result = supervisor.process_user_request(
                    session_id=session_id,
                    user_message="/push",
                    channel="telegram",
                    auto_push=True,
                )
                await self.send_message(chat_id, result["ai_response"])
            elif data == "action_show_tasks":
                await self.answer_callback_query(cb_id, text="할 일 목록 조회 중...")
                result = supervisor.process_user_request(
                    session_id=session_id,
                    user_message="/gtd-today",
                    channel="telegram",
                    auto_push=False,
                )
                await self.send_message(chat_id, result["ai_response"])
            elif data == "action_show_next":
                await self.answer_callback_query(cb_id, text="Next Actions 조회 중...")
                result = supervisor.process_user_request(
                    session_id=session_id,
                    user_message="/gtd",
                    channel="telegram",
                    auto_push=False,
                )
                await self.send_message(chat_id, result["ai_response"])
            elif data == "action_prompt_diary":
                await self.answer_callback_query(cb_id, text="오늘 일기 쓰기")
                diary_prompt = (
                    "✍️ **오늘 하루는 어떠셨나요?**\n\n"
                    "오늘 있었던 특별한 일, 생각, 운동, 감정을 편하게 메시지로 보내주세요.\n"
                    "제가 오늘 자 라이프로그(`logs/daily/YYYY-MM-DD.md`)에 깔끔하게 정리해 드릴게요! 😊"
                )
                supervisor.session_service.add_message(session_id=session_id, role="assistant", content=diary_prompt)
                await self.send_message(chat_id, diary_prompt)
            else:
                await self.answer_callback_query(cb_id, text=f"알 수 없는 요청: {data}")
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
                "• `/done [내용]`: 1순위 또는 지정된 GTD 태스크 완료 처리 및 Git 푸시\n"
                "• `/url`: 웹 대시보드 최신 접속 주소 확인\n"
                "• `/sync`: 연결된 GTD 저장소 원격 최신화(git pull)\n"
                "• `/push`: 로컬 라이프로그 및 GTD 원격 저장소로 푸시(git push)\n"
                "• `/status`: 서버 및 깃허브 연동 상태 확인\n"
                "• `/help`: 도움말 확인"
            )
            await self.send_message(chat_id, welcome_text)
            return

        if text.startswith("/help"):
            help_text = (
                "📖 **Watson 텔레그램 봇 사용법**\n\n"
                "1. **자유로운 대화**: '오늘 날씨 어때?', '1부터 30 중에 골라줘' 등 무엇이든 물어보세요.\n"
                "2. **할 일 / 일정 브리핑**: '오늘 해야할 일 정리해줘' 또는 'gtd 레포 최신화하고 다시 알려줘'라고 물어보세요.\n"
                "3. **일과 공유 & 자동 제안**: '오늘 헬스장 다녀옴', '프로젝트 킥오프 완료' 등 일과를 말하면 비서가 기록할지 여부를 버튼으로 여쭤봅니다.\n"
                "4. **사진 전송**: 일상 사진이나 영수증을 보내면 오늘 라이프로그에 사진이 첨부됩니다.\n"
                "5. **직접 기록**: `/log 러닝 5km 완료` 명령어로 바로 기록할 수 있습니다.\n"
                "6. **1순위 태스크 완료**: `/done` 명령어로 현재 1순위 태스크를 원터치 완료(- [x]) 처리하고 GitHub에 푸시합니다.\n"
                "7. **웹 대시보드 주소**: `/url` 명령어로 브라우저에서 접속할 수 있는 실시간 Cloudflare HTTPS 주소를 확인합니다.\n"
                "8. **GTD 레포 최신화**: `/sync` 또는 'gtd 레포 최신화' 명령어로 원격 저장소를 즉시 동기화(pull)합니다.\n"
                "9. **GitHub 원격 푸시**: `/push` 또는 '푸시해줘', '깃 푸시' 명령어로 로컬 커밋을 원격 저장소로 안전하게 푸시합니다.\n"
                "10. **인터랙티브 인라인 버튼**: 정기 브리핑(아침 08:30, 저녁 20:00) 하단의 원클릭 버튼을 터치해 타이핑 없이 즉시 조작할 수 있습니다."
            )
            await self.send_message(chat_id, help_text)
            return

        if text.startswith("/status"):
            settings_service = SettingsService()
            gtd_status = settings_service.get_status()
            tunnel_url = self._get_tunnel_url()
            url_line = f"• 웹 대시보드 URL: {tunnel_url}\n" if tunnel_url else ""
            status_text = (
                "🤖 **Watson Agent 시스템 상태**\n\n"
                f"• 서버 상태: 정상 가동 중 (Online 24/7)\n"
                f"• 세션 ID: `telegram:{chat_id}`\n"
                f"{url_line}"
                f"• GTD 작업 경로: `{gtd_status['gtd_path']}`\n"
                f"• Git 격리 연동: {'✅ 전용 레포 활성' if gtd_status['is_git_repo'] else '📁 로컬 보관 전용'}\n"
                f"• 최근 동기화 시간: {get_now().strftime('%Y-%m-%d %H:%M:%S')} ({settings.TIMEZONE})"
            )
            await self.send_message(chat_id, status_text)
            return

        if text.startswith(("/url", "/web", "/link", "/tunnel")):
            tunnel_url = self._get_tunnel_url()
            if tunnel_url:
                url_msg = (
                    "🌐 **Watson 웹 대시보드 접속 주소**\n\n"
                    f"🔗 {tunnel_url}\n\n"
                    "• 🏠 **에이전트 허브 포털**: `/`\n"
                    "• 🤖 **왓슨 비서 콘솔**: `/watson`\n"
                    "• 💻 **개발 에이전트 DevBot**: `/dev`\n\n"
                    "💡 브라우저 로그인 창에서 설정된 ID/PW를 입력해 주세요."
                )
            else:
                url_msg = (
                    "🌐 **Watson 웹 대시보드 접속 안내**\n\n"
                    "현재 외부 Cloudflare Tunnel 주소를 확인할 수 없습니다. 로컬(`http://localhost:8000`) 또는 터널 서비스를 확인해 주세요."
                )
            await self.send_message(chat_id, url_msg)
            return

        if text.startswith("/gtd"):
            settings_service = SettingsService()
            status = settings_service.get_status()
            gtd_msg = (
                "📁 **Watson GTD 저장소 상태**\n\n"
                f"• 작업 경로: `{status['gtd_path']}`\n"
                f"• 격리 모드: {'외부 저장소 (External)' if status['is_external'] else '로컬 봇 기본 (Default)'}\n"
                f"• Git 버전 관리: {'✅ 활성화 (Git Active)' if status['is_git_repo'] else '📁 로컬 파일 전용 (Local Only)'}\n"
                f"• GTD 체계 감지: `{status['structure_type']}` (Inbox: {'있음' if status['has_inbox'] else '없음'})\n\n"
                "💡 웹 대시보드(설정)에서 GTD 작업 경로를 언제든 변경하실 수 있습니다."
            )
            await self.send_message(chat_id, gtd_msg)
            return

        # 2-2. 사진(Photo) 수신 처리
        if "photo" in msg:
            photos = msg["photo"]
            caption = msg.get("caption", "").strip() or "일상 사진 메모"
            largest_photo = photos[-1]  # 가장 고화질 사진
            file_id = largest_photo["file_id"]

            now = get_now()
            year_str = now.strftime("%Y")
            month_str = now.strftime("%m")
            filename = f"tg_{int(now.timestamp())}_{file_id[:8]}.jpg"

            settings_service = SettingsService()
            gtd_path = settings_service.get_gtd_path()

            # GTD 저장소 내 attachments 또는 web static 경로에 저장
            if os.path.exists(os.path.join(gtd_path, "attachments")):
                rel_path = f"attachments/{year_str}/{month_str}/{filename}"
                abs_path = os.path.join(gtd_path, rel_path)
            else:
                rel_path = f"static/images/{year_str}/{month_str}/{filename}"
                abs_path = os.path.join(settings.REPO_PATH, "app", rel_path)

            success = await self.download_file(file_id, abs_path)
            if success:
                # 마크다운 라이프로그에 이미지 링크 추가
                agent_service = AgentService(base_dir=gtd_path)
                git_service = GitService(repo_path=gtd_path)
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
            elif intent in [
                "task_briefing_morning",
                "task_briefing_evening",
                "task_briefing",
                "repo_sync_and_briefing",
            ]:
                mode = (
                    "morning"
                    if intent == "task_briefing_morning"
                    else ("evening" if intent == "task_briefing_evening" else "auto")
                )
                if mode == "auto":
                    now_hour = get_now().hour
                    mode = "morning" if 5 <= now_hour < 14 else "evening"
                reply_markup = self.get_briefing_keyboard(mode=mode)
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
