from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.telegram_service import TelegramService

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


class TelegramCommandItem(BaseModel):
    command: str = Field(..., description="명령어 이름 (1-32자 소문자 영문/숫자/언더스코어)")
    description: str = Field(..., description="명령어 한글/영문 설명 (1-256자)")
    enabled: bool = Field(True, description="활성화 여부")


class TelegramCommandsUpdateRequest(BaseModel):
    commands: list[TelegramCommandItem] = Field(..., description="설정할 명령어 목록")
    sync_to_telegram: bool = Field(True, description="Telegram Bot API 즉시 동기화 여부")


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):  # noqa: B008
    """텔레그램 웹훅(Webhook) 업데이트 수신 엔드포인트."""
    update_data = await request.json()
    telegram_service = TelegramService()
    await telegram_service.process_update(update=update_data, db=db)
    return {"status": "ok"}


@router.get("/status")
def telegram_status() -> dict[str, Any]:
    """텔레그램 봇 연동 설정 상태를 확인합니다."""
    telegram_service = TelegramService()
    configured_cmds = TelegramService.get_configured_commands()
    return {
        "configured": telegram_service.is_configured(),
        "allowed_chat_ids_count": len(telegram_service.allowed_chat_ids),
        "allowed_chat_ids": telegram_service.allowed_chat_ids,
        "total_commands_count": len(configured_cmds),
        "active_commands_count": sum(1 for c in configured_cmds if c.get("enabled", True)),
    }


@router.get("/commands")
def get_telegram_commands() -> dict[str, Any]:
    """설정된 텔레그램 봇 메뉴 명령어 목록 및 활성화 상태를 조회합니다 (ADR-040, ADR-041)."""
    telegram_service = TelegramService()
    commands = TelegramService.get_configured_commands()
    return {
        "configured": telegram_service.is_configured(),
        "count": len(commands),
        "total_count": len(commands),
        "active_count": sum(1 for c in commands if c.get("enabled", True)),
        "commands": commands,
    }


@router.post("/commands")
async def update_telegram_commands(payload: TelegramCommandsUpdateRequest) -> dict[str, Any]:
    """텔레그램 봇 메뉴 명령어 목록을 저장하고 선택 시 Telegram Bot API에 즉시 반영합니다 (ADR-041)."""
    telegram_service = TelegramService()
    saved = TelegramService.save_configured_commands([c.model_dump() for c in payload.commands])
    synced = False
    if payload.sync_to_telegram and telegram_service.is_configured():
        synced = await telegram_service.set_my_commands()

    return {
        "status": "ok",
        "saved_count": len(saved),
        "active_count": sum(1 for c in saved if c.get("enabled", True)),
        "synced": synced,
        "commands": saved,
    }


@router.post("/commands/reset")
async def reset_telegram_commands() -> dict[str, Any]:
    """텔레그램 봇 메뉴 명령어를 기본 14종으로 초기화하고 Telegram에 반영합니다 (ADR-041)."""
    telegram_service = TelegramService()
    reset_cmds = TelegramService.reset_to_default_commands()
    synced = False
    if telegram_service.is_configured():
        synced = await telegram_service.set_my_commands()

    return {
        "status": "ok",
        "reset_count": len(reset_cmds),
        "active_count": sum(1 for c in reset_cmds if c.get("enabled", True)),
        "synced": synced,
        "commands": reset_cmds,
    }


@router.post("/setup-commands")
async def setup_telegram_commands() -> dict[str, Any]:
    """텔레그램 봇 메뉴 명령어를 Telegram Bot API에 등록/갱신합니다 (ADR-040)."""
    telegram_service = TelegramService()
    success = await telegram_service.set_my_commands()
    configured_cmds = TelegramService.get_configured_commands()
    active_count = sum(1 for c in configured_cmds if c.get("enabled", True))
    return {
        "status": "ok" if success else "failed",
        "configured": telegram_service.is_configured(),
        "commands_count": active_count,
        "commands": configured_cmds,
    }


