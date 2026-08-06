import logging
from aiogram import Bot, Dispatcher
from interfaces.base import AbstractMessengerInterface
from interfaces.telegram.handlers import register_handlers
from services.productivity import ProductivityService
from services.ai_agent import WatsonAIEngine

class TelegramInterface(AbstractMessengerInterface):
    def __init__(self, token: str, service: ProductivityService):
        super().__init__(service)
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.ai_engine = WatsonAIEngine()
        router = register_handlers(self.service, self.ai_engine)
        self.dp.include_router(router)

    async def start(self):
        logging.info("Starting Telegram Bot interface with AI Agent...")
        await self.dp.start_polling(self.bot)

    async def stop(self):
        logging.info("Stopping Telegram Bot interface...")
        await self.bot.session.close()
