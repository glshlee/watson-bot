from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verify_web_auth
from app.db.database import get_db
from app.services.supervisor_service import SupervisorService

router = APIRouter(dependencies=[Depends(verify_web_auth)])


class TriggerPushRequest(BaseModel):
    mode: str = "auto"
    chat_id: str | None = None


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
