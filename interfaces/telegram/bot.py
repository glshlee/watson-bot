import logging
from aiogram import Bot, Dispatcher
from interfaces.base import AbstractMessengerInterface
from interfaces.telegram.handlers import register_handlers
from services.productivity import ProductivityService

class TelegramInterface(AbstractMessengerInterface):
    def __init__(self, token: str, service: ProductivityService):
        super().__init__(service)
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        router = register_handlers(self.service)
        self.dp.include_router(router)

    async def start(self):
        logging.info("Starting Telegram Bot interface...")
        await self.dp.start_polling(self.bot)

    async def stop(self):
        logging.info("Stopping Telegram Bot interface...")
        await self.bot.session.close()
