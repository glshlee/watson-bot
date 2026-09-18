from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
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
def chat_with_agent(
    payload: ChatRequest,
    db: Session = Depends(get_db),  # noqa: B008
    x_fast_mode: str | None = Header(default=None),
):
    """왓슨 라이프로그 AI 에이전트 인터랙티브 대화 엔드포인트."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    is_fast = bool(x_fast_mode and x_fast_mode.lower() in ("true", "1"))
    supervisor = SupervisorService(db=db, fast_mode=is_fast)
    return supervisor.process_user_request(
        session_id=payload.session_id,
        user_message=payload.message,
        category=payload.category,
        channel="web",
        auto_push=payload.auto_push,
    )


@router.post("/api/dev/chat")
def chat_with_dev_agent(
    payload: DevChatRequest,
    db: Session = Depends(get_db),  # noqa: B008
    x_fast_mode: str | None = Header(default=None),
):
    """DevBot 소프트웨어 엔지니어링 에이전트 대화 엔드포인트 (ADR-018)."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    is_fast = bool(x_fast_mode and x_fast_mode.lower() in ("true", "1"))
    dev_service = DevAgentService(db=db, fast_mode=is_fast)
    return dev_service.process_dev_request(
        session_id=payload.session_id,
        user_message=payload.message,
        channel="web",
    )
