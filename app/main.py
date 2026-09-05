import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.database import init_db
from app.routers import telegram_router, web_router
from app.services.telegram_service import TelegramService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("watson.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 수명 주기 관리: DB 마이그레이션 및 텔레그램 봇 폴링 백그라운드 태스크 구동."""
    init_db()

    telegram_service = TelegramService()
    polling_task = None
    if telegram_service.is_configured():
        logger.info("🤖 Starting background Telegram Bot polling task...")
        polling_task = asyncio.create_task(telegram_service.start_polling())
    else:
        logger.info("ℹ️ Telegram bot token not set. Running in Web Dashboard mode only.")

    yield

    if polling_task:
        logger.info("🛑 Stopping Telegram Bot polling task...")
        telegram_service.stop_polling()
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Watson GitHub LifeLog AI Agent", version="1.0.0", lifespan=lifespan)

# Mount Static files
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include Routers
app.include_router(web_router.router)
app.include_router(telegram_router.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
