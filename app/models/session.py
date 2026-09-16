from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.config import get_now
from app.db.database import Base


def kst_now():
    """한국 표준시(KST) 기준 현재 시간을 반환합니다 (ADR-013)."""
    return get_now()


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True, index=True)  # session_id or telegram:chat_id
    title = Column(String(255), nullable=False, default="New Conversation")
    channel = Column(String(32), nullable=False, default="web")  # "telegram" or "web"
    agent_type = Column(String(32), nullable=False, default="watson", index=True)  # "watson" or "dev"
    pending_log = Column(Text, nullable=True)  # JSON 문자열: {"content": "...", "category": "..."}
    created_at = Column(DateTime, default=kst_now)
    updated_at = Column(DateTime, default=kst_now, onupdate=kst_now)

    messages = relationship(
        "ChatMessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessageModel.id",
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # "user" or "assistant" or "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=kst_now)

    session = relationship("SessionModel", back_populates="messages")
