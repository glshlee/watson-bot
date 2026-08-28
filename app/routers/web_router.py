from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.supervisor_service import SupervisorService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

class LogRequest(BaseModel):
    session_id: str = "web_default_session"
    message: str
    category: str = "Daily Notes & Diary"
    auto_push: bool = True

@router.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@router.post("/api/log")
def create_log(payload: LogRequest, db: Session = Depends(get_db)):  # noqa: B008
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
