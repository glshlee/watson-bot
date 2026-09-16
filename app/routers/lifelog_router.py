from __future__ import annotations

import os
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verify_web_auth
from app.config import get_now
from app.db.database import get_db
from app.routers.briefing_router import TriggerPushRequest
from app.services.agent_service import AgentService
from app.services.git_service import GitService
from app.services.heatmap_service import HeatmapService
from app.services.search_service import SearchService
from app.services.session_service import SessionService
from app.services.settings_service import SettingsService
from app.services.setup_service import SetupService
from app.services.supervisor_service import SupervisorService
from app.services.vision_service import VisionService
from app.services.weekly_review_service import WeeklyReviewService

router = APIRouter(dependencies=[Depends(verify_web_auth)])


class LifelogSaveRequest(BaseModel):
    date: str
    content: str
    commit_msg: str | None = None
    auto_push: bool = True


@router.get("/api/search")
def search_lifelog(
    q: str = Query(..., description="검색할 키워드"),
    limit: int = Query(10, ge=1, le=50, description="최대 결과 개수"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """라이프로그 및 GTD 마크다운 고속 검색 엔드포인트 (ADR-043)."""
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


@router.post("/api/vision/analyze")
async def analyze_vision_image(
    file: UploadFile = File(...),  # noqa: B008
    caption: str = Form(""),
):
    """업로드된 사진에 대한 Vision AI 멀티모달 시각 분석 API (ADR-044)."""
    settings_service = SettingsService()
    gtd_path = settings_service.get_gtd_path()

    now = get_now()
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    clean_filename = os.path.basename(file.filename or "upload.jpg")
    safe_name = f"web_{int(now.timestamp())}_{clean_filename}"

    attachments_dir = os.path.join(gtd_path, "attachments", year_str, month_str)
    os.makedirs(attachments_dir, exist_ok=True)
    abs_path = os.path.join(attachments_dir, safe_name)
    rel_path = f"attachments/{year_str}/{month_str}/{safe_name}"

    contents = await file.read()
    with open(abs_path, "wb") as f:  # noqa: ASYNC230
        f.write(contents)

    vision_service = VisionService()
    analysis = vision_service.analyze_image(
        image_path=abs_path,
        user_caption=caption,
        image_rel_path=rel_path,
    )

    return {
        "status": "success",
        "data": vision_service.to_dict(analysis),
        "draft_card": vision_service.format_draft_card(analysis),
    }


@router.post("/api/vision/upload-and-log")
async def upload_and_log_image(
    file: UploadFile = File(...),  # noqa: B008
    caption: str = Form(""),
    session_id: str = Form("web_default_session"),
    auto_confirm: bool = Form(False),
    db: Session = Depends(get_db),  # noqa: B008
):
    """사진 업로드 후 2단계 사전 검토 또는 즉시 기록을 수행하는 통합 API (ADR-044)."""
    settings_service = SettingsService()
    gtd_path = settings_service.get_gtd_path()

    now = get_now()
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    clean_filename = os.path.basename(file.filename or "upload.jpg")
    safe_name = f"web_{int(now.timestamp())}_{clean_filename}"

    attachments_dir = os.path.join(gtd_path, "attachments", year_str, month_str)
    os.makedirs(attachments_dir, exist_ok=True)
    abs_path = os.path.join(attachments_dir, safe_name)
    rel_path = f"attachments/{year_str}/{month_str}/{safe_name}"

    contents = await file.read()
    with open(abs_path, "wb") as f:  # noqa: ASYNC230
        f.write(contents)

    vision_service = VisionService()
    analysis = vision_service.analyze_image(
        image_path=abs_path,
        user_caption=caption,
        image_rel_path=rel_path,
    )

    session_service = SessionService(db=db)

    if auto_confirm:
        agent_service = AgentService(base_dir=gtd_path)
        git_service = GitService(repo_path=gtd_path)

        filepath = agent_service.append_or_update_lifelog(
            content=analysis.markdown_content,
            category=analysis.suggested_category,
            date_obj=now,
        )
        if analysis.gtd_task:
            agent_service.append_to_gtd_inbox(analysis.gtd_task)

        date_str = now.strftime("%Y-%m-%d")
        commit_msg = f"docs(lifelog): [{analysis.suggested_category}] {analysis.summary[:30]} ({date_str}) [{session_id}]"
        git_service.sync_and_commit_push(commit_message=commit_msg, file_path=filepath)

        session_service.add_message(
            session_id=session_id,
            role="user",
            content=f"[사진 업로드: {caption or clean_filename}]",
        )
        session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=f"📷 사진 시각 분석 완료 및 라이프로그 반영:\n\n{analysis.markdown_content}",
        )

        return {
            "status": "success",
            "logged": True,
            "message": f"라이프로그 [{analysis.suggested_category}]에 안전하게 기록 및 푸시되었습니다.",
            "data": vision_service.to_dict(analysis),
        }
    else:
        draft_card = vision_service.format_draft_card(analysis)
        session_service.set_pending_log(
            session_id=session_id,
            content=analysis.markdown_content,
            category=analysis.suggested_category,
            gtd_task=analysis.gtd_task,
            is_dual=bool(analysis.gtd_task),
        )

        session_service.add_message(
            session_id=session_id,
            role="user",
            content=f"[사진 업로드: {caption or clean_filename}]",
        )
        session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=draft_card,
        )

        return {
            "status": "success",
            "logged": False,
            "draft_card": draft_card,
            "data": vision_service.to_dict(analysis),
        }


@router.get("/api/lifelog/heatmap")
def get_lifelog_heatmap(
    days: int = Query(365, ge=7, le=730, description="조회 일수 (기본값: 365)"),
):
    """ADR-045: 연간/월간 잔디(Contribution Heatmap) 및 기록 통계 API."""
    gtd_path = SettingsService().get_gtd_path()
    heatmap_service = HeatmapService(base_dir=gtd_path)
    data = heatmap_service.get_heatmap_data(days=days)
    return {"status": "success", "data": data}


@router.get("/api/lifelog/file")
def get_lifelog_file(
    date: str = Query(..., description="조회할 일자 (YYYY-MM-DD)"),
):
    """ADR-045: 특정 일자의 마크다운 일일 로그 원문 및 메타데이터 조회 API."""
    gtd_path = SettingsService().get_gtd_path()
    heatmap_service = HeatmapService(base_dir=gtd_path)
    data = heatmap_service.get_lifelog_content(date_str=date)
    return {"status": "success", "data": data}


@router.post("/api/lifelog/save")
def save_lifelog_file(
    req: LifelogSaveRequest,
):
    """ADR-045: 마크다운 일일 로그 인플레이스 저장 및 원자적 Git 커밋/푸시 API."""
    gtd_path = SettingsService().get_gtd_path()
    heatmap_service = HeatmapService(base_dir=gtd_path)
    res = heatmap_service.save_lifelog_content(
        date_str=req.date,
        content=req.content,
        commit_msg=req.commit_msg,
        auto_push=req.auto_push,
    )
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=str(res.get("error", "파일 저장 실패")))
    return {"status": "success", "data": res}


@router.get("/api/system/setup-status")
def get_system_setup_status() -> dict[str, Any]:
    """ADR-046: 1-Click 셀프호스팅 셋업 및 시스템 배포 준비 상태 진단 API."""
    service = SetupService()
    data = service.get_setup_status()
    report = service.format_status_report()
    return {"status": "success", "data": data, "report": report}
