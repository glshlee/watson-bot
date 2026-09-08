import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("watson.agent")


class AgentService:
    """
    마크다운 라이프로그 및 GTD 오케스트레이션 서비스 (ADR-001, ADR-007 준수).
    지정된 base_dir(GTD 저장소)의 체계(inbox.md, logs/daily/ 등)를 자동 감지하여
    적절한 마크다운 파일에 정제된 일상 기록 및 GTD 할 일을 작성합니다.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(os.path.expanduser(base_dir))

    def has_gtd_inbox(self) -> bool:
        """GTD 수집함(inbox.md) 파일 존재 여부 확인"""
        return os.path.exists(os.path.join(self.base_dir, "gtd", "inbox.md")) or os.path.exists(
            os.path.join(self.base_dir, "inbox.md")
        )

    def has_daily_logs_structure(self) -> bool:
        """logs/daily 폴더 구조 존재 여부 확인"""
        return os.path.exists(os.path.join(self.base_dir, "logs", "daily"))

    def get_gtd_inbox_filepath(self) -> str:
        """GTD inbox 파일 경로 반환 (우선순위: gtd/inbox.md -> inbox.md)"""
        gtd_path = os.path.join(self.base_dir, "gtd", "inbox.md")
        if os.path.exists(gtd_path):
            return gtd_path
        root_inbox = os.path.join(self.base_dir, "inbox.md")
        if os.path.exists(root_inbox):
            return root_inbox
        # Default target if none exists yet but requested
        os.makedirs(os.path.join(self.base_dir, "gtd"), exist_ok=True)
        return gtd_path

    def append_to_gtd_inbox(self, content: str) -> str:
        """
        GTD Inbox(수집함)의 '## 💬 빠른 메모 / 캡처' 섹션에 할 일/메모를 추가합니다.
        """
        filepath = self.get_gtd_inbox_filepath()
        if not os.path.exists(filepath):
            initial_content = """# 📥 GTD Inbox (수집함)

## 💬 빠른 메모 / 캡처 (Watson & Quick Capture)

## 💡 아이디어 / 검토 대기
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(initial_content)

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Target section header
        target_headers = [
            "## 💬 빠른 메모 / 캡처",
            "## 📥 GTD Inbox",
            "## 빠른 메모",
            "## Inbox",
        ]
        target_idx = -1
        for i, line in enumerate(lines):
            for th in target_headers:
                if th.lower() in line.lower():
                    target_idx = i
                    break
            if target_idx != -1:
                break

        # Check if item already starts with task format
        task_item = content.strip()
        if not task_item.startswith("- ["):
            task_item = f"- [ ] {task_item} *(Watson 캡처)*\n"
        else:
            task_item = f"{task_item}\n"

        if target_idx != -1:
            lines.insert(target_idx + 1, task_item)
        else:
            lines.append(f"\n## 💬 빠른 메모 / 캡처 (Watson & Quick Capture)\n{task_item}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

        logger.info(f"Appended task to GTD inbox: {filepath}")
        return filepath

    def get_lifelog_filepath(self, date_obj: datetime | None = None) -> str:
        if date_obj is None:
            date_obj = datetime.now(timezone.utc)

        filename = date_obj.strftime("%Y-%m-%d.md")

        # 1. logs/daily/ 구조가 존재하는 경우 해당 경로 우선 사용
        if self.has_daily_logs_structure():
            dir_path = os.path.join(self.base_dir, "logs", "daily")
            os.makedirs(dir_path, exist_ok=True)
            return os.path.join(dir_path, filename)

        # 2. 기본 lifelogs/YYYY/MM/ 경로 구조 (하위 호환성)
        year_str = date_obj.strftime("%Y")
        month_str = date_obj.strftime("%m")
        dir_path = os.path.join(self.base_dir, "lifelogs", year_str, month_str)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, filename)

    def append_or_update_lifelog(
        self,
        content: str,
        category: str = "Daily Notes & Diary",
        date_obj: datetime | None = None,
    ) -> str:
        # Check if this category represents a GTD Inbox task and repository has GTD structure
        gtd_task_categories = ["GTD Inbox", "GTD", "Task", "Todo", "Quick Capture", "할일"]
        if any(cat.lower() in category.lower() for cat in gtd_task_categories) and self.has_gtd_inbox():
            return self.append_to_gtd_inbox(content)

        filepath = self.get_lifelog_filepath(date_obj)
        current_date_str = (date_obj or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
        time_str = (date_obj or datetime.now(timezone.utc)).strftime("%H:%M")

        if not os.path.exists(filepath):
            # Create new file with template based on structure
            if self.has_daily_logs_structure():
                initial_template = f"""# {current_date_str}

## 📝 오늘 하루 일상 및 기록 (Daily Journal)

## 📅 주요 일정 (Schedule)

## ✅ 오늘 완료한 일 (Completed GTD Tasks)

## 💡 순간 메모 / 캡처 (Capture)
"""
            else:
                initial_template = f"""# 📅 Life Log - {current_date_str}

## 📝 Daily Notes & Diary

## 🏋️ Workout & Health

## 💡 Ideas & Thoughts

## 🖼️ Media & Attachments
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(initial_template)

        with open(filepath, "r", encoding="utf-8") as f:
            file_lines = f.readlines()

        # Match header target
        header_target = category
        cat_lower = category.lower()

        if self.has_daily_logs_structure():
            if any(k in cat_lower for k in ["workout", "health", "diary", "daily note"]):
                header_target = "## 📝 오늘 하루 일상 및 기록"
            elif any(k in cat_lower for k in ["idea", "thought", "capture", "메모"]):
                header_target = "## 💡 순간 메모 / 캡처"
            elif any(k in cat_lower for k in ["task", "schedule", "할일", "일정"]):
                header_target = "## 📅 주요 일정"
            elif "완료" in cat_lower or "complete" in cat_lower:
                header_target = "## ✅ 오늘 완료한 일"
            else:
                header_target = f"## 📝 {category}"
        else:
            if "Daily Notes" in category:
                header_target = "## 📝 Daily Notes & Diary"
            elif "Workout" in category or "Health" in category:
                header_target = "## 🏋️ Workout & Health"
            elif "Idea" in category or "Thought" in category:
                header_target = "## 💡 Ideas & Thoughts"
            elif "Media" in category or "Attachment" in category:
                header_target = "## 🖼️ Media & Attachments"
            else:
                header_target = f"## 📝 {category}" if not category.startswith("##") else category

        entry_line = f"- [{time_str}] {content}\n"

        # Find header line index
        target_idx = -1
        for i, line in enumerate(file_lines):
            if header_target.lower() in line.lower():
                target_idx = i
                break

        if target_idx != -1:
            file_lines.insert(target_idx + 1, entry_line)
        else:
            file_lines.append(f"\n{header_target}\n{entry_line}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(file_lines)

        return filepath
