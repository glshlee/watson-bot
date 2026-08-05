import asyncio
import logging
import time
import config
from storage.git_markdown import GitMarkdownStorageRepository
from services.productivity import ProductivityService
from interfaces.telegram.bot import TelegramInterface

logging.basicConfig(level=config.LOG_LEVEL)

async def heartbeat_loop(filepath: str = "/tmp/agy_bot.heartbeat"):
    """Watchdog(Engineer Bot) 오판 방지를 위한 하트비트 파일 주기적 갱신"""
    while True:
        try:
            with open(filepath, "w") as f:
                f.write(str(time.time()))
        except Exception as e:
            logging.error(f"Heartbeat update failed: {e}")
        await asyncio.sleep(30)

async def main():
    if not config.BOT_TOKEN:
        logging.error("BOT_TOKEN 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return

    # Watchdog 하트비트 백그라운드 태스크 시작
    asyncio.create_task(heartbeat_loop())

    # 1. Storage Layer (Life Log Repository Markdown Sync)
    storage = GitMarkdownStorageRepository(repo_path=config.LIFE_LOG_PATH)

    # 2. Domain & Core Service Layer
    service = ProductivityService(storage=storage)

    # 3. Interface Layer (Current: Telegram)
    app_interface = TelegramInterface(token=config.BOT_TOKEN, service=service)

    try:
        await app_interface.start()
    finally:
        await app_interface.stop()

if __name__ == "__main__":
    asyncio.run(main())
