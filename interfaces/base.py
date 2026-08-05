from abc import ABC, abstractmethod
from services.productivity import ProductivityService

class AbstractMessengerInterface(ABC):
    def __init__(self, service: ProductivityService):
        self.service = service

    @abstractmethod
    async def start(self):
        """메신저 인스턴스 실행 및 이벤트 루프 대기"""
        pass

    @abstractmethod
    async def stop(self):
        """메신저 인스턴스 안전 종료"""
        pass
