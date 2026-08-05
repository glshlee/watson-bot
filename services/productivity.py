from typing import List
from storage.base import AbstractStorageRepository
from domain.models import TodoItem, MemoItem, ScheduleItem

class ProductivityService:
    def __init__(self, storage: AbstractStorageRepository):
        self.storage = storage

    async def create_todo(self, user_id: int, title: str) -> TodoItem:
        return await self.storage.add_todo(user_id=user_id, title=title)

    async def get_all_todos(self, user_id: int) -> List[TodoItem]:
        return await self.storage.list_todos(user_id=user_id)

    async def toggle_todo_status(self, user_id: int, todo_id: str) -> bool:
        return await self.storage.toggle_todo(user_id=user_id, todo_id=todo_id)

    async def create_memo(self, user_id: int, content: str) -> MemoItem:
        return await self.storage.add_memo(user_id=user_id, content=content)

    async def get_all_memos(self, user_id: int) -> List[MemoItem]:
        return await self.storage.list_memos(user_id=user_id)

    async def create_schedule(self, user_id: int, title: str, remind_time: str) -> ScheduleItem:
        return await self.storage.add_schedule(user_id=user_id, title=title, remind_time=remind_time)

    async def get_all_schedules(self, user_id: int) -> List[ScheduleItem]:
        return await self.storage.list_schedules(user_id=user_id)
