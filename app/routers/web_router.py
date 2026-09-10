from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verify_web_auth
from app.db.database import get_db
from app.services.dev_agent_service import DevAgentService
from app.services.supervisor_service import SupervisorService

router = APIRouter(dependencies=[Depends(verify_web_auth)])
templates = Jinja2Templates(directory="app/templates")

class ChatRequest(BaseModel):
    session_id: str = "web_default_session"
    message: str
    category: str = "Daily Notes & Diary"
    auto_push: bool = True

class DevChatRequest(BaseModel):
    session_id: str = "dev_default_session"
    message: str

class UpdateSessionRequest(BaseModel):
    title: str

@router.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """에이전트 허브 대시보드 포털 렌더링 (ADR-018)."""
    return templates.TemplateResponse(request=request, name="portal.html")

@router.get("/watson", response_class=HTMLResponse)
def read_watson_console(request: Request):
    """왓슨 라이프로그 & 개인 비서 인터랙티브 콘솔 렌더링."""
    return templates.TemplateResponse(request=request, name="index.html")

@router.get("/dev", response_class=HTMLResponse)
def read_dev_console(request: Request):
    """DevBot 소프트웨어 엔지니어링 & 코드 옵스 콘솔 렌더링 (ADR-018)."""
    return templates.TemplateResponse(request=request, name="dev.html")

@router.get("/api/hub/status")
def get_hub_status(db: Session = Depends(get_db)):  # noqa: B008
    supervisor = SupervisorService(db=db)
    watson_sessions = supervisor.session_service.list_sessions(agent_type="watson")
    dev_service = DevAgentService(db=db)
    dev_sessions = supervisor.session_service.list_sessions(agent_type="dev")
    dev_ws = dev_service.get_workspace_status()

    return {
        "hub_title": "Watson Agent Workspace",
        "total_agents": 2,
        "agents": [
            {
                "id": "watson",
                "name": "Watson",
                "role": "Personal Butler & LifeLog",
                "status": "online",
                "badge": "24/7 Active",
                "description": "개인 일상 기록, 생각/감정 회고, GTD 일정 관리 및 텔레그램 연동",
                "route": "/watson",
                "session_count": len(watson_sessions),
                "channel": "Web & Telegram",
            },
            {
                "id": "dev",
                "name": "DevBot",
                "role": "Software Engineering & Code Ops",
                "status": "ready",
                "badge": "Ready",
                "description": "코드베이스 분석, Git 버전 관리(Diff/Status), 터미널 도구 실행 및 아키텍처 리팩터링",
                "route": "/dev",
                "session_count": len(dev_sessions),
                "workspace": dev_ws.get("workspace", "watson-bot"),
                "branch": dev_ws.get("branch", "main"),
            },
        ],
    }

@router.post("/api/dev/chat")
def chat_with_dev_agent(payload: DevChatRequest, db: Session = Depends(get_db)):  # noqa: B008
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    dev_service = DevAgentService(db=db)
    return dev_service.process_dev_request(
        session_id=payload.session_id,
        user_message=payload.message,
        channel="web",
    )

@router.get("/api/dev/sessions")
def get_dev_sessions(db: Session = Depends(get_db)):  # noqa: B008
    dev_service = DevAgentService(db=db)
    return dev_service.session_service.list_sessions(agent_type="dev")

@router.get("/api/dev/status")
def get_dev_status(db: Session = Depends(get_db)):  # noqa: B008
    dev_service = DevAgentService(db=db)
    return dev_service.get_workspace_status()

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
    return supervisor.list_sessions(agent_type="watson")

@router.get("/api/sessions/{session_id}/history")
def get_session_history(session_id: str, db: Session = Depends(get_db)):  # noqa: B008
    supervisor = SupervisorService(db=db)
    history = supervisor.get_session_history(session_id)
    session = supervisor.session_service.get_session(session_id)
    title = session.title if session else session_id
    channel = session.channel if session else "web"
    return {"session_id": session_id, "title": title, "channel": channel, "history": history}

@router.patch("/api/sessions/{session_id}")
def update_session_title(session_id: str, payload: UpdateSessionRequest, db: Session = Depends(get_db)):  # noqa: B008
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
    supervisor = SupervisorService(db=db)
    success = supervisor.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id}

@router.post("/api/sessions/{session_id}/clear")
def clear_session_messages(session_id: str, db: Session = Depends(get_db)):  # noqa: B008
    supervisor = SupervisorService(db=db)
    success = supervisor.clear_session_messages(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id}


@router.get("/api/briefing")
def get_briefing(
    mode: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008
):
    """아침/저녁 맞춤형 GTD 브리핑 조회 엔드포인트 (ADR-024)."""
    supervisor = SupervisorService(db=db)
    result = supervisor.get_briefing(mode=mode)
    return {"status": "success", "data": result}


@router.get("/api/briefing/schedule")
def get_briefing_schedule(
    db: Session = Depends(get_db),  # noqa: B008
):
    """브리핑 정기 스케줄 및 오늘 일일 일정 조회 엔드포인트 (ADR-025)."""
    supervisor = SupervisorService(db=db)
    result = supervisor.get_briefing_schedule()
    return {"status": "success", "data": result}


