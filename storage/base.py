from abc import ABC, abstractmethod
from typing import List
from domain.models import TodoItem, MemoItem, ScheduleItem

class AbstractStorageRepository(ABC):
    @abstractmethod
    async def add_todo(self, user_id: int, title: str, due_date: str = None) -> TodoItem:
        pass

    @abstractmethod
    async def list_todos(self, user_id: int) -> List[TodoItem]:
        pass

    @abstractmethod
    async def toggle_todo(self, user_id: int, todo_id: str) -> bool:
        pass

    @abstractmethod
    async def add_memo(self, user_id: int, content: str) -> MemoItem:
        pass

    @abstractmethod
    async def list_memos(self, user_id: int) -> List[MemoItem]:
        pass

    @abstractmethod
    async def add_schedule(self, user_id: int, title: str, remind_time: str) -> ScheduleItem:
        pass

    @abstractmethod
    async def list_schedules(self, user_id: int) -> List[ScheduleItem]:
        pass

    @abstractmethod
    async def append_chat_log(self, user_id: int, user_text: str, watson_reply: str):
        """대화 기록(Chat Log)을 깃허브 마크다운 노트 파일에 추가"""
        pass
