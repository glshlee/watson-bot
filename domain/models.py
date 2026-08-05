from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class TodoItem:
    id: str
    title: str
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[str] = None
    user_id: Optional[int] = None

@dataclass
class MemoItem:
    id: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    user_id: Optional[int] = None

@dataclass
class ScheduleItem:
    id: str
    title: str
    remind_time: str  # YYYY-MM-DD HH:MM
    user_id: Optional[int] = None
