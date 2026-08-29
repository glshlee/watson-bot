from datetime import datetime, timezone
from typing import Any, Dict, List
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
    ) -> Dict[str, Any]:
        # 1. DB 세션 생성 및 사용자 메시지 저장
        self.session_service.get_or_create_session(session_id=session_id, channel=channel)
        self.session_service.add_message(session_id=session_id, role="user", content=user_message)
        history = self.session_service.get_session_history(session_id=session_id)

        # 2. 지능형 AI 챗봇 대화 답변 생성
        ai_response = self.llm_provider.generate_response(prompt=user_message, history=history)
        self.session_service.add_message(session_id=session_id, role="assistant", content=ai_response)

        # 3. 라이프 로그 마크다운 파일 작성 및 Git 처리
        filepath = self.agent_service.append_or_update_lifelog(
            content=user_message,
            category=category,
            date_obj=datetime.now(timezone.utc),
        )

        push_success = False
        if auto_push:
            commit_msg = f"docs(lifelog): Add log for {datetime.now(timezone.utc).strftime('%Y-%m-%d')} [{session_id}]"
            push_success = self.git_service.sync_and_commit_push(commit_message=commit_msg, file_path=filepath)

        return {
            "session_id": session_id,
            "filepath": filepath,
            "ai_response": ai_response,
            "git_pushed": push_success,
            "history": self.session_service.get_session_history(session_id=session_id)
        }

    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.session_service.get_session_history(session_id=session_id)

    def list_sessions(self) -> List[Any]:
        return self.session_service.list_sessions()
