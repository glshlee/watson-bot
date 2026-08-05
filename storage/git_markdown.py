import os
import re
import uuid
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import git

from storage.base import AbstractStorageRepository
from domain.models import TodoItem, MemoItem, ScheduleItem

class GitMarkdownStorageRepository(AbstractStorageRepository):
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.watson_dir = self.repo_path / "02_personal" / "watson"
        self.watson_dir.mkdir(parents=True, exist_ok=True)
        self._init_git()

    def _init_git(self):
        try:
            self.repo = git.Repo(self.repo_path)
        except Exception as e:
            self.repo = None
            print(f"Git repo error at {self.repo_path}: {e}")

    def _get_user_filepath(self, user_id: int) -> Path:
        return self.watson_dir / f"user_{user_id}.md"

    def _commit_and_push(self, message: str):
        if not self.repo:
            return
        try:
            self.repo.git.add(A=True)
            if self.repo.is_dirty(untracked_files=True):
                self.repo.index.commit(f"[watson-bot] {message}")
                origin = self.repo.remote(name='origin')
                origin.push()
        except Exception as e:
            print(f"Git sync failed: {e}")

    def _read_markdown(self, filepath: Path) -> dict:
        data = {"todos": [], "memos": [], "schedules": []}
        if not filepath.exists():
            return data

        content = filepath.read_text(encoding="utf-8")
        current_section = None

        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("## Todos"):
                current_section = "todos"
                continue
            elif line_str.startswith("## Memos"):
                current_section = "memos"
                continue
            elif line_str.startswith("## Schedules"):
                current_section = "schedules"
                continue

            if current_section == "todos" and line_str.startswith("- ["):
                completed = line_str.startswith("- [x]")
                match = re.search(r"<!-- id:(.*?) -->", line_str)
                item_id = match.group(1) if match else str(uuid.uuid4())[:8]
                title = re.sub(r"- \[[ x\]] ", "", line_str)
                title = re.sub(r"<!-- id:.*? -->", "", title).strip()
                data["todos"].append(TodoItem(id=item_id, title=title, completed=completed))

            elif current_section == "memos" and line_str.startswith("- "):
                match = re.search(r"<!-- id:(.*?) -->", line_str)
                item_id = match.group(1) if match else str(uuid.uuid4())[:8]
                text = line_str[2:]
                text = re.sub(r"<!-- id:.*? -->", "", text).strip()
                data["memos"].append(MemoItem(id=item_id, content=text))

            elif current_section == "schedules" and line_str.startswith("- "):
                match = re.search(r"<!-- id:(.*?) -->", line_str)
                item_id = match.group(1) if match else str(uuid.uuid4())[:8]
                text = line_str[2:]
                text = re.sub(r"<!-- id:.*? -->", "", text).strip()
                data["schedules"].append(ScheduleItem(id=item_id, title=text, remind_time=""))

        return data

    def _write_markdown(self, filepath: Path, data: dict):
        lines = [f"# Watson Life Log - User {filepath.stem.replace('user_', '')}\n"]
        
        lines.append("## Todos")
        for item in data["todos"]:
            check = "x" if item.completed else " "
            lines.append(f"- [{check}] {item.title} <!-- id:{item.id} -->")

        lines.append("\n## Memos")
        for item in data["memos"]:
            lines.append(f"- {item.content} <!-- id:{item.id} -->")

        lines.append("\n## Schedules")
        for item in data["schedules"]:
            lines.append(f"- {item.title} <!-- id:{item.id} -->")

        filepath.write_text("\n".join(lines), encoding="utf-8")

    async def add_todo(self, user_id: int, title: str, due_date: str = None) -> TodoItem:
        filepath = self._get_user_filepath(user_id)
        data = self._read_markdown(filepath)
        todo = TodoItem(id=str(uuid.uuid4())[:8], title=title, due_date=due_date, user_id=user_id)
        data["todos"].append(todo)
        self._write_markdown(filepath, data)
        self._commit_and_push(f"Add todo: {title}")
        return todo

    async def list_todos(self, user_id: int) -> List[TodoItem]:
        filepath = self._get_user_filepath(user_id)
        data = self._read_markdown(filepath)
        return data["todos"]

    async def toggle_todo(self, user_id: int, todo_id: str) -> bool:
        filepath = self._get_user_filepath(user_id)
        data = self._read_markdown(filepath)
        updated = False
        for item in data["todos"]:
            if item.id == todo_id:
                item.completed = not item.completed
                updated = True
                break
        if updated:
            self._write_markdown(filepath, data)
            self._commit_and_push(f"Toggle todo: {todo_id}")
        return updated

    async def add_memo(self, user_id: int, content: str) -> MemoItem:
        filepath = self._get_user_filepath(user_id)
        data = self._read_markdown(filepath)
        memo = MemoItem(id=str(uuid.uuid4())[:8], content=content, user_id=user_id)
        data["memos"].append(memo)
        self._write_markdown(filepath, data)
        self._commit_and_push(f"Add memo: {content[:15]}")
        return memo

    async def list_memos(self, user_id: int) -> List[MemoItem]:
        filepath = self._get_user_filepath(user_id)
        data = self._read_markdown(filepath)
        return data["memos"]

    async def add_schedule(self, user_id: int, title: str, remind_time: str) -> ScheduleItem:
        filepath = self._get_user_filepath(user_id)
        data = self._read_markdown(filepath)
        schedule = ScheduleItem(id=str(uuid.uuid4())[:8], title=title, remind_time=remind_time, user_id=user_id)
        data["schedules"].append(schedule)
        self._write_markdown(filepath, data)
        self._commit_and_push(f"Add schedule: {title}")
        return schedule

    async def list_schedules(self, user_id: int) -> List[ScheduleItem]:
        filepath = self._get_user_filepath(user_id)
        data = self._read_markdown(filepath)
        return data["schedules"]
