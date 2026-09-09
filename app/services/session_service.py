import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.session import ChatMessageModel, SessionModel


class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(
        self,
        session_id: str,
        channel: str = "web",
        title: str = "New Conversation",
        agent_type: str = "watson",
    ) -> SessionModel:
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            session = SessionModel(id=session_id, channel=channel, title=title, agent_type=agent_type)
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> SessionModel | None:
        return self.db.query(SessionModel).filter(SessionModel.id == session_id).first()

    def add_message(self, session_id: str, role: str, content: str) -> ChatMessageModel:
        session = self.get_or_create_session(session_id)
        msg = ChatMessageModel(session_id=session_id, role=role, content=content)
        self.db.add(msg)
        session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_session_history(self, session_id: str, limit: int = 50) -> list[dict[str, str]]:
        messages = (
            self.db.query(ChatMessageModel)
            .filter(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.id.desc())
            .limit(limit)
            .all()
        )
        # Re-sort chronologically
        messages.reverse()
        return [{"role": str(msg.role), "content": str(msg.content)} for msg in messages]

    def set_pending_log(self, session_id: str, content: str, category: str = "Daily Notes & Diary") -> None:
        """비서가 제안한 보류 라이프로그 후보를 세션에 저장합니다."""
        session = self.get_or_create_session(session_id)
        payload = json.dumps({"content": content, "category": category}, ensure_ascii=False)
        session.pending_log = payload  # type: ignore[assignment]
        self.db.commit()

    def get_pending_log(self, session_id: str) -> dict[str, str] | None:
        """세션에 보류 중인 라이프로그 후보를 조회합니다."""
        session = self.get_or_create_session(session_id)
        pending = getattr(session, "pending_log", None)
        if not pending:
            return None
        try:
            return json.loads(str(pending))
        except (json.JSONDecodeError, TypeError):
            return None

    def clear_pending_log(self, session_id: str) -> None:
        """세션의 보류 라이프로그 후보를 초기화합니다."""
        session = self.get_or_create_session(session_id)
        session.pending_log = None  # type: ignore[assignment]
        self.db.commit()

    def update_session_title(self, session_id: str, title: str) -> SessionModel | None:
        """세션 제목을 수정합니다."""
        session = self.get_session(session_id)
        if not session:
            return None
        session.title = title.strip() or "Untitled Session"  # type: ignore[assignment]
        session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        self.db.commit()
        self.db.refresh(session)
        return session

    def auto_update_session_title(self, session_id: str, user_message: str) -> None:
        """새 세션의 첫 발화 시 사용자 메시지 기반으로 스마트 제목 자동 생성"""
        session = self.get_session(session_id)
        if not session:
            return
        default_titles = {"New Conversation", "새 대화", "새 세션"}
        if session.title in default_titles or session.title.startswith("web_session_") or session.title == session.id:
            clean = user_message.strip().replace("\n", " ")
            if clean.startswith("/log "):
                clean = clean[5:].strip()
            new_title = clean[:26] + ("..." if len(clean) > 26 else "")
            if new_title:
                session.title = new_title  # type: ignore[assignment]
                self.db.commit()

    def delete_session(self, session_id: str) -> bool:
        """세션과 관련 메시지를 완전히 삭제합니다."""
        session = self.get_session(session_id)
        if not session:
            return False
        self.db.delete(session)
        self.db.commit()
        return True

    def clear_session_messages(self, session_id: str) -> bool:
        """세션은 유지한 채 대화 내역(메시지)만 초기화합니다."""
        session = self.get_session(session_id)
        if not session:
            return False
        self.db.query(ChatMessageModel).filter(ChatMessageModel.session_id == session_id).delete()
        session.pending_log = None  # type: ignore[assignment]
        session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        self.db.commit()
        return True

    def list_sessions(self, agent_type: str | None = None) -> list[dict[str, Any]]:
        """세션 목록을 풍부한 메타데이터와 함께 반환합니다."""
        query = self.db.query(SessionModel)
        if agent_type:
            query = query.filter(SessionModel.agent_type == agent_type)
        sessions = query.order_by(SessionModel.updated_at.desc()).all()
        result = []
        for s in sessions:
            msg_count = len(s.messages) if s.messages else 0
            last_msg = s.messages[-1].content if s.messages else ""
            if len(last_msg) > 50:
                last_msg = last_msg[:50] + "..."
            result.append({
                "id": str(s.id),
                "title": str(s.title),
                "channel": str(s.channel),
                "agent_type": str(getattr(s, "agent_type", "watson") or "watson"),
                "created_at": s.created_at.isoformat() if s.created_at else "",
                "updated_at": s.updated_at.isoformat() if s.updated_at else "",
                "message_count": msg_count,
                "last_message": last_msg,
            })
        return result

