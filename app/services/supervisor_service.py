from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.agent_service import AgentService
from app.services.git_service import GitService
from app.services.llm_provider import LLMProvider
from app.services.session_service import SessionService


class SupervisorService:
    def __init__(self, db: Session, base_dir: str = "."):
        self.session_service = SessionService(db)
        self.agent_service = AgentService(base_dir=base_dir)
        self.git_service = GitService(repo_path=base_dir)
        self.llm_provider = LLMProvider()

    def process_user_request(
        self,
        session_id: str,
        user_message: str,
        category: str = "Daily Notes & Diary",
        channel: str = "web",
        auto_push: bool = True,
    ) -> dict[str, Any]:
        # 1. DB 세션 생성 및 보류 기록/히스토리 조회
        self.session_service.get_or_create_session(session_id=session_id, channel=channel)
        pending_log = self.session_service.get_pending_log(session_id=session_id)
        history = self.session_service.get_session_history(session_id=session_id)

        # 2. 사용자 메시지 DB 저장
        self.session_service.add_message(session_id=session_id, role="user", content=user_message)

        # 3. 비서 의도 분석 및 답변 생성 (ADR-004)
        intent_res = self.llm_provider.analyze_and_respond(
            prompt=user_message,
            history=history,
            pending_log=pending_log,
        )

        filepath = None
        push_success = False

        # 4. 의도별 분기 처리
        if intent_res.intent in ["log_confirm", "log_explicit"]:
            # (A) 승인되었거나 직접 요청된 유의미한 라이프로그 -> 마크다운 기록 & Git 커밋 (옵션 A)
            content_to_log = intent_res.log_content or user_message
            target_cat = intent_res.category or category

            filepath = self.agent_service.append_or_update_lifelog(
                content=content_to_log,
                category=target_cat,
                date_obj=datetime.now(timezone.utc),
            )

            if auto_push:
                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                commit_msg = f"docs(lifelog): [{target_cat}] {content_to_log[:30]} ({date_str}) [{session_id}]"
                push_success = self.git_service.sync_and_commit_push(commit_message=commit_msg, file_path=filepath)

            self.session_service.clear_pending_log(session_id=session_id)

        elif intent_res.intent == "log_suggest":
            # (B) 비서가 라이프로그 기록을 제안 -> 세션에 보류 보관 (Git 커밋 X, 마크다운 수정 X)
            suggested_content = intent_res.log_content or user_message
            suggested_cat = intent_res.category or category
            self.session_service.set_pending_log(
                session_id=session_id,
                content=suggested_content,
                category=suggested_cat,
            )

        elif intent_res.intent == "log_reject":
            # (C) 사용자가 제안 거절 -> 보류 기록 초기화 (Git 커밋 X, 마크다운 수정 X)
            self.session_service.clear_pending_log(session_id=session_id)

        # 5. AI 응답 DB 저장
        self.session_service.add_message(session_id=session_id, role="assistant", content=intent_res.ai_response)

        return {
            "session_id": session_id,
            "intent": intent_res.intent,
            "filepath": filepath,
            "ai_response": intent_res.ai_response,
            "git_pushed": push_success,
            "history": self.session_service.get_session_history(session_id=session_id),
            "pending_log": self.session_service.get_pending_log(session_id=session_id),
        }

    def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        return self.session_service.get_session_history(session_id=session_id)

    def list_sessions(self) -> list[Any]:
        return self.session_service.list_sessions()
