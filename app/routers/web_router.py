from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import verify_web_auth
from app.db.database import get_db
from app.routers import (
    briefing_router,
    chat_router,
    lifelog_router,
    session_router,
)
from app.services.dev_agent_service import DevAgentService
from app.services.supervisor_service import SupervisorService

router = APIRouter(dependencies=[Depends(verify_web_auth)])
templates = Jinja2Templates(directory="app/templates")

# Mount Domain Routers (Modular Architecture - ADR-051)
router.include_router(chat_router.router)
router.include_router(session_router.router)
router.include_router(briefing_router.router)
router.include_router(lifelog_router.router)


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
    """에이전트 허브 포털 상태 요약 조회 (ADR-018)."""
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


@router.get("/api/dev/status")
def get_dev_status(db: Session = Depends(get_db)):  # noqa: B008
    """DevBot 워크스페이스 상태 조회 (ADR-018)."""
    dev_service = DevAgentService(db=db)
    return dev_service.get_workspace_status()


@router.get("/api/dev/roadmap")
def get_dev_roadmap(db: Session = Depends(get_db)):  # noqa: B008
    """DevBot 로드맵 데이터 및 진행률 조회 (ADR-057)."""
    dev_service = DevAgentService(db=db)
    data = dev_service.parse_roadmap_data()
    data["markdown"] = dev_service.format_roadmap_report()
    return data


@router.get("/api/dev/skills")
def get_dev_skills(db: Session = Depends(get_db)):  # noqa: B008
    """DevBot 사용 가능 .agents/skills 카탈로그 조회 (ADR-057)."""
    dev_service = DevAgentService(db=db)
    skills = dev_service.get_available_skills()
    return {
        "total_skills": len(skills),
        "skills": skills,
        "markdown": dev_service.format_skills_catalog(),
    }


@router.get("/api/dev/skills/{skill_name}")
def get_dev_skill_detail(skill_name: str, db: Session = Depends(get_db)):  # noqa: B008
    """DevBot 특정 스킬 상세 조회 (ADR-057)."""
    dev_service = DevAgentService(db=db)
    skills = dev_service.get_available_skills()
    target = skill_name.strip().lower()
    for s in skills:
        if target == s["id"].lower() or target == s["name"].lower() or target in s["id"].lower():
            return s
    raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

