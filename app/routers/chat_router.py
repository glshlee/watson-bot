from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verify_web_auth
from app.db.database import get_db
from app.services.dev_agent_service import DevAgentService
from app.services.supervisor_service import SupervisorService

router = APIRouter(dependencies=[Depends(verify_web_auth)])


class ChatRequest(BaseModel):
    session_id: str = "web_default_session"
    message: str
    category: str = "Daily Notes & Diary"
    auto_push: bool = True


class DevChatRequest(BaseModel):
    session_id: str = "dev_default_session"
    message: str


@router.post("/api/chat")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):  # noqa: B008
    """왓슨 라이프로그 AI 에이전트 인터랙티브 대화 엔드포인트."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    supervisor = SupervisorService(db=db)
    return supervisor.process_user_request(
        session_id=payload.session_id,
        user_message=payload.message,
        category=payload.category,
        channel="web",
        auto_push=payload.auto_push,
    )


@router.post("/api/dev/chat")
def chat_with_dev_agent(payload: DevChatRequest, db: Session = Depends(get_db)):  # noqa: B008
    """DevBot 소프트웨어 엔지니어링 에이전트 대화 엔드포인트 (ADR-018)."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    dev_service = DevAgentService(db=db)
    return dev_service.process_dev_request(
        session_id=payload.session_id,
        user_message=payload.message,
        channel="web",
    )
