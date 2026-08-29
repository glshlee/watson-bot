from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.supervisor_service import SupervisorService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

class ChatRequest(BaseModel):
    session_id: str = "web_default_session"
    message: str
    category: str = "Daily Notes & Diary"
    auto_push: bool = True

@router.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@router.post("/api/chat")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):  # noqa: B008
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    supervisor = SupervisorService(db=db)
    result = supervisor.process_user_request(
        session_id=payload.session_id,
        user_message=payload.message,
        category=payload.category,
        channel="web",
        auto_push=payload.auto_push
    )
    return result

@router.get("/api/sessions")
def get_sessions(db: Session = Depends(get_db)):  # noqa: B008
    supervisor = SupervisorService(db=db)
    sessions = supervisor.list_sessions()
    return [{"id": s.id, "title": s.title, "channel": s.channel, "updated_at": s.updated_at.isoformat()} for s in sessions]

@router.get("/api/sessions/{session_id}/history")
def get_session_history(session_id: str, db: Session = Depends(get_db)):  # noqa: B008
    supervisor = SupervisorService(db=db)
    history = supervisor.get_session_history(session_id)
    return {"session_id": session_id, "history": history}
