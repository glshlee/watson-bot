from typing import Any

from sqlalchemy.orm import Session

from app.services.agy_runner import AGYRunner
from app.services.session_service import SessionService


class SupervisorService:
    """
    유저 세션을 관리하고, 모든 파일 조작 및 라이프 로그 기록 업무를
    AGY (Antigravity) AI 에이전트 본체에 직접 위임·조율하는 슈퍼바이저 서비스.
    """
    def __init__(self, db: Session, base_dir: str = "."):
        self.session_service = SessionService(db)
        self.agy_runner = AGYRunner(workspace_path=base_dir)

    def process_user_request(
        self,
        session_id: str,
        user_message: str,
        category: str = "Daily Notes & Diary",
        channel: str = "web",
        auto_push: bool = True,
    ) -> dict[str, Any]:
        # 1. DB 세션 생성 및 사용자 메시지 저장
        self.session_service.get_or_create_session(session_id=session_id, channel=channel)
        self.session_service.add_message(session_id=session_id, role="user", content=user_message)
        history = self.session_service.get_session_history(session_id=session_id)

        # 2. AGY AI 에이전트에게 전적으로 라이프 로그 작성 및 대화 위임 (AGY 자율 실행)
        agy_result = self.agy_runner.run_agent_task(
            user_message=user_message,
            category=category,
            history=history
        )

        ai_response = agy_result["ai_response"]

        # 3. AGY 답변을 DB 세션에 저장
        self.session_service.add_message(session_id=session_id, role="assistant", content=ai_response)

        return {
            "session_id": session_id,
            "filepath": agy_result["filepath"],
            "ai_response": ai_response,
            "git_pushed": agy_result["git_pushed"],
            "history": self.session_service.get_session_history(session_id=session_id)
        }

    def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        return self.session_service.get_session_history(session_id=session_id)

    def list_sessions(self) -> list[Any]:
        return self.session_service.list_sessions()
