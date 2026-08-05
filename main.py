import asyncio
import logging
import config
from storage.git_markdown import GitMarkdownStorageRepository
from services.productivity import ProductivityService
from interfaces.telegram.bot import TelegramInterface

logging.basicConfig(level=config.LOG_LEVEL)

async def main():
    if not config.BOT_TOKEN:
        logging.error("BOT_TOKEN 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return

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
