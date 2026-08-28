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

    def list_sessions(self) -> list[SessionModel]:
        return self.db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
