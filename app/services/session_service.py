import json

from sqlalchemy.orm import Session

from app.models.session import ChatMessageModel, SessionModel


class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(self, session_id: str, channel: str = "web", title: str = "New Conversation") -> SessionModel:
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            session = SessionModel(id=session_id, channel=channel, title=title)
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
        return session

    def add_message(self, session_id: str, role: str, content: str) -> ChatMessageModel:
        self.get_or_create_session(session_id)
        msg = ChatMessageModel(session_id=session_id, role=role, content=content)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_session_history(self, session_id: str, limit: int = 20) -> list[dict[str, str]]:
        messages = (
            self.db.query(ChatMessageModel)
            .filter(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.id.desc())
            .limit(limit)
            .all()
        )
        # Re-sort chronologically
        messages.reverse()
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def set_pending_log(self, session_id: str, content: str, category: str = "Daily Notes & Diary") -> None:
        """비서가 제안한 보류 라이프로그 후보를 세션에 저장합니다."""
        session = self.get_or_create_session(session_id)
        payload = json.dumps({"content": content, "category": category}, ensure_ascii=False)
        session.pending_log = payload
        self.db.commit()

    def get_pending_log(self, session_id: str) -> dict[str, str] | None:
        """세션에 보류 중인 라이프로그 후보를 조회합니다."""
        session = self.get_or_create_session(session_id)
        if not session.pending_log:
            return None
        try:
            return json.loads(session.pending_log)
        except (json.JSONDecodeError, TypeError):
            return None

    def clear_pending_log(self, session_id: str) -> None:
        """세션의 보류 라이프로그 후보를 초기화합니다."""
        session = self.get_or_create_session(session_id)
        session.pending_log = None
        self.db.commit()

    def list_sessions(self) -> list[SessionModel]:
        return self.db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
