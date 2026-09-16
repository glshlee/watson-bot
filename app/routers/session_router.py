from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verify_web_auth
from app.db.database import get_db
from app.services.dev_agent_service import DevAgentService
from app.services.supervisor_service import SupervisorService

router = APIRouter(dependencies=[Depends(verify_web_auth)])


class UpdateSessionRequest(BaseModel):
    title: str


@router.get("/api/sessions")
def get_sessions(db: Session = Depends(get_db)):  # noqa: B008
    """왓슨 비서 세션 목록 조회 엔드포인트."""
    supervisor = SupervisorService(db=db)
    return supervisor.list_sessions(agent_type="watson")


@router.get("/api/dev/sessions")
def get_dev_sessions(db: Session = Depends(get_db)):  # noqa: B008
    """DevBot 세션 목록 조회 엔드포인트 (ADR-018)."""
    dev_service = DevAgentService(db=db)
    return dev_service.session_service.list_sessions(agent_type="dev")


@router.get("/api/sessions/{session_id}/history")
def get_session_history(session_id: str, db: Session = Depends(get_db)):  # noqa: B008
    """특정 세션의 대화 히스토리 및 메타데이터 조회 엔드포인트."""
    supervisor = SupervisorService(db=db)
    history = supervisor.get_session_history(session_id)
    session = supervisor.session_service.get_session(session_id)
    title = session.title if session else session_id
    channel = session.channel if session else "web"
    return {"session_id": session_id, "title": title, "channel": channel, "history": history}


@router.patch("/api/sessions/{session_id}")
def update_session_title(session_id: str, payload: UpdateSessionRequest, db: Session = Depends(get_db)):  # noqa: B008
    """세션 제목 변경 엔드포인트 (ADR-017)."""
    clean_title = payload.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Session title cannot be empty")
    supervisor = SupervisorService(db=db)
    updated = supervisor.update_session_title(session_id, clean_title)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id, "title": updated.title}


@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):  # noqa: B008
    """세션 삭제 엔드포인트 (ADR-017)."""
    supervisor = SupervisorService(db=db)
    success = supervisor.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id}


@router.post("/api/sessions/{session_id}/clear")
def clear_session_messages(session_id: str, db: Session = Depends(get_db)):  # noqa: B008
    """세션 메시지 전체 비우기 엔드포인트 (ADR-017)."""
    supervisor = SupervisorService(db=db)
    success = supervisor.clear_session_messages(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id}
