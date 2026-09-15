from fastapi import APIRouter, Depends, HTTPException, Query, Request
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


class TriggerPushRequest(BaseModel):
    mode: str = "auto"
    chat_id: str | None = None


@router.get("/api/briefing/scheduler/status")
def get_scheduler_status(request: Request):
    """정기 브리핑 백그라운드 스케줄러 상태 조회 엔드포인트 (ADR-026)."""
    from app.services.briefing_scheduler import BriefingScheduler

    scheduler: BriefingScheduler | None = getattr(request.app.state, "briefing_scheduler", None)
    if not scheduler:
        scheduler = BriefingScheduler()
    return {"status": "success", "data": scheduler.get_scheduler_status()}


@router.post("/api/briefing/trigger-push")
async def trigger_briefing_push(
    request: Request,
    payload: TriggerPushRequest | None = None,
):
    """텔레그램 브리핑 푸시 즉시 발송/테스트 엔드포인트 (ADR-026)."""
    from app.services.briefing_scheduler import BriefingScheduler

    scheduler: BriefingScheduler | None = getattr(request.app.state, "briefing_scheduler", None)
    if not scheduler:
        scheduler = BriefingScheduler()
    mode = payload.mode if payload else "auto"
    target_chat_ids = [payload.chat_id] if payload and payload.chat_id else None
    result = await scheduler.dispatch_briefing(mode=mode, target_chat_ids=target_chat_ids)
    return {"status": "success", "data": result}


@router.get("/api/search")
def search_lifelog(
    q: str = Query(..., description="검색할 키워드"),
    limit: int = Query(10, ge=1, le=50, description="최대 결과 개수"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """라이프로그 및 GTD 마크다운 고속 검색 엔드포인트 (ADR-043)."""
    from app.services.search_service import SearchService
    from app.services.settings_service import SettingsService

    settings_service = SettingsService()
    gtd_path = settings_service.get_gtd_path()
    search_service = SearchService(base_dir=gtd_path)

    results = search_service.search(query=q, max_results=limit)
    markdown_card = search_service.format_search_results_card(query=q, results=results)

    return {
        "status": "success",
        "query": q,
        "total_count": len(results),
        "results": results,
        "markdown": markdown_card,
    }


@router.get("/api/weekly")
def get_weekly_review(
    days: int = Query(7, ge=1, le=30, description="조회 기간 (일수)"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """주간 결산 회고 리포트 조회 엔드포인트 (ADR-043)."""
    from app.services.settings_service import SettingsService
    from app.services.supervisor_service import SupervisorService
    from app.services.weekly_review_service import WeeklyReviewService

    supervisor = SupervisorService(db=db)
    settings_service = SettingsService()
    gtd_path = settings_service.get_gtd_path()

    weekly_service = WeeklyReviewService(
        base_dir=gtd_path,
        llm_provider=supervisor.llm_provider,
    )
    result = weekly_service.generate_weekly_review(days=days)
    return {"status": "success", "data": result}


@router.post("/api/weekly/trigger-push")
async def trigger_weekly_push(
    request: Request,
    payload: TriggerPushRequest | None = None,
):
    """텔레그램 주간 결산 리포트 푸시 즉시 발송/테스트 엔드포인트 (ADR-043)."""
    from app.services.briefing_scheduler import BriefingScheduler

    scheduler: BriefingScheduler | None = getattr(request.app.state, "briefing_scheduler", None)
    if not scheduler:
        scheduler = BriefingScheduler()
    target_chat_ids = [payload.chat_id] if payload and payload.chat_id else None
    result = await scheduler.dispatch_weekly_review(target_chat_ids=target_chat_ids)
    return {"status": "success", "data": result}



