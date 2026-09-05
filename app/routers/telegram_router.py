from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.telegram_service import TelegramService

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):  # noqa: B008
    """텔레그램 웹훅(Webhook) 업데이트 수신 엔드포인트."""
    update_data = await request.json()
    telegram_service = TelegramService()
    await telegram_service.process_update(update=update_data, db=db)
    return {"status": "ok"}


@router.get("/status")
def telegram_status():
    """텔레그램 봇 연동 설정 상태를 확인합니다."""
    telegram_service = TelegramService()
    return {
        "configured": telegram_service.is_configured(),
        "allowed_chat_ids_count": len(telegram_service.allowed_chat_ids),
    }
