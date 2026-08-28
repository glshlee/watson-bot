from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.agent_service import AgentService
from app.services.git_service import GitService
from app.services.session_service import SessionService


class SupervisorService:
    def __init__(self, db: Session, base_dir: str = "."):
        self.session_service = SessionService(db)
        self.agent_service = AgentService(base_dir=base_dir)
        self.git_service = GitService(repo_path=base_dir)

    def process_user_request(
        self,
        session_id: str,
        user_message: str,
        category: str = "Daily Notes & Diary",
        channel: str = "web",
        auto_push: bool = True
    ) -> dict[str, Any]:
        # 1. Session Context Retrieval
        self.session_service.get_or_create_session(session_id=session_id, channel=channel)
        self.session_service.add_message(session_id=session_id, role="user", content=user_message)
        history = self.session_service.get_session_history(session_id=session_id)

        # 2. Lifelog Markdown Generation / Update
        filepath = self.agent_service.append_or_update_lifelog(
            content=user_message,
            category=category,
            date_obj=datetime.now(timezone.utc)
        )

        # 3. AI Assistant Response Generation (Mock/Rule or LLM prompt)
        ai_response = f"기록이 정상적으로 '{filepath}'에 반영되었습니다.\n(작성 내용: {user_message})"
        self.session_service.add_message(session_id=session_id, role="assistant", content=ai_response)

        # 4. Git Push Execution
        push_success = False
        if auto_push:
            commit_msg = f"docs(lifelog): Add log for {datetime.now(timezone.utc).strftime('%Y-%m-%d')} [{session_id}]"
            push_success = self.git_service.sync_and_commit_push(commit_message=commit_msg, file_path=filepath)

        return {
            "session_id": session_id,
            "filepath": filepath,
            "ai_response": ai_response,
            "git_pushed": push_success,
            "history_count": len(history) + 1
        }
