from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import TYPE_CHECKING

from app.config import get_app_timezone, get_now

if TYPE_CHECKING:
    from app.services.gtd_service import GTDService

logger = logging.getLogger("watson.lifelog")


class LifelogService:
    """
    일일 마크다운 라이프로그(Daily LifeLog) 전담 관리 서비스 (ADR-001, ADR-013, ADR-032, ADR-053).
    - 일일 로그 디렉토리(logs/daily/ 또는 lifelogs/YYYY/MM/) 감지 및 경로 계산
    - KST 타임존 정규화 및 [HH:MM] 타임스탬프 엔트리 서식화
    - 카테고리별 섹션 헤더 탐색 및 중복 방지(Deduplication) 추가
    - 완료된 GTD 태스크의 수술적 이관(Surgical Transfer) 수신 및 오늘자 로그 기록
    - 당일 일일 로그 마크다운 실시간 읽기
    """

    def __init__(self, base_dir: str = ".", gtd_service: GTDService | None = None):
        self.base_dir = os.path.abspath(os.path.expanduser(base_dir))
        self.gtd_service = gtd_service

    def set_gtd_service(self, gtd_service: GTDService) -> None:
        """순환 참조 방지를 위한 GTD 서비스 바인딩."""
        self.gtd_service = gtd_service

    def normalize_datetime(self, date_obj: datetime | None = None) -> datetime:
        """
        입력된 date_obj를 애플리케이션 설정 타임존(기본값: Asia/Seoul, KST)으로 정규화합니다 (ADR-013).
        - None인 경우: get_now() 반환
        - naive datetime인 경우: 설정 타임존으로 로컬라이징
        - aware datetime인 경우: 설정 타임존으로 변환(astimezone)
        """
        if date_obj is None:
            return get_now()
        if date_obj.tzinfo is None:
            return date_obj.replace(tzinfo=get_app_timezone())
        return date_obj.astimezone(get_app_timezone())

    def has_daily_logs_structure(self) -> bool:
        """logs/daily 폴더 구조 존재 여부 확인"""
        return os.path.exists(os.path.join(self.base_dir, "logs", "daily"))

    def get_lifelog_filepath(self, date_obj: datetime | None = None) -> str:
        """
        지정된 날짜의 일일 로그 마크다운 파일 절대 경로를 반환합니다.
        (우선순위: logs/daily/YYYY-MM-DD.md -> lifelogs/YYYY/MM/YYYY-MM-DD.md)
        """
        date_obj = self.normalize_datetime(date_obj)
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
        """
        비정형 텍스트를 마크다운 서식으로 포맷팅하여 적절한 카테고리 헤더 아래에 기록합니다.
        카테고리가 GTD Inbox 할 일인 경우 연결된 GTD 서비스로 라우팅합니다.
        """
        date_obj = self.normalize_datetime(date_obj)

        # GTD Inbox 라우팅 검사
        gtd_task_categories = ["GTD Inbox", "GTD", "Task", "Todo", "Quick Capture", "할일"]
        if (
            any(cat.lower() in category.lower() for cat in gtd_task_categories)
            and self.gtd_service
            and self.gtd_service.has_gtd_inbox()
        ):
            return self.gtd_service.append_to_gtd_inbox(content)

        filepath = self.get_lifelog_filepath(date_obj)
        current_date_str = date_obj.strftime("%Y-%m-%d")
        time_str = date_obj.strftime("%H:%M")

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

        # 1. 멀티라인 줄바꿈 정규화 (불릿 서식 깨짐 방지)
        cleaned_content = " ".join(line.strip() for line in content.splitlines() if line.strip())

        # 2. 중복 기록 방지 가드 (Deduplication Guard)
        existing_text = "".join(file_lines)
        check_snippet = cleaned_content[:30] if len(cleaned_content) >= 30 else cleaned_content
        if check_snippet and check_snippet in existing_text:
            logger.info("Content already recorded in %s, skipping duplicate append: %s", filepath, check_snippet)
            return filepath

        entry_line = f"- [{time_str}] {cleaned_content}\n"

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

    def transfer_completed_task_to_daily_log(
        self,
        task_text: str,
        date_obj: datetime | None = None,
    ) -> bool:
        """
        완료된 GTD 태스크를 당일 데일리 로그(logs/daily/YYYY-MM-DD.md)의
        '## ✅ 오늘 완료한 일 (Completed GTD Tasks)' 섹션으로 이관(Surgical Transfer)합니다 (ADR-032).
        """
        date_obj = self.normalize_datetime(date_obj)
        filepath = self.get_lifelog_filepath(date_obj)
        current_date_str = date_obj.strftime("%Y-%m-%d")

        if not os.path.exists(filepath):
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

## ✅ 오늘 완료한 일 (Completed GTD Tasks)

## 💡 Ideas & Thoughts

## 🖼️ Media & Attachments
"""
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(initial_template)
            except OSError as e:
                logger.error(f"Failed to create daily log for task transfer: {e}")
                return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            logger.error(f"Failed to read daily log {filepath}: {e}")
            return False

        clean_task = task_text.strip()
        if clean_task.startswith(("- [ ]", "- [x]")):
            clean_task = clean_task[5:].strip()
        new_task_line = f"- [x] {clean_task}\n"

        # 중복 검사: 데일리 로그에 이미 완료 형태로 존재하는지 확인
        clean_task_norm = re.sub(r"\s+", " ", clean_task.lower())
        for line in lines:
            line_s = line.strip()
            if line_s.startswith("- [x]"):
                line_norm = re.sub(r"\s+", " ", line_s[5:].strip().lower())
                if clean_task_norm in line_norm or line_norm in clean_task_norm:
                    logger.info(f"Task already completed in daily log: {clean_task}")
                    return True

        # 완료 섹션 헤더 탐색
        target_idx = -1
        target_headers = [
            "## ✅ 오늘 완료한 일",
            "## 🎯 오늘 한 일",
            "## 완료한 일",
            "## Completed Tasks",
            "## 📝 오늘 하루 일상 및 기록",
        ]
        for i, line in enumerate(lines):
            for th in target_headers:
                if th.lower() in line.lower():
                    target_idx = i
                    break
            if target_idx != -1:
                break

        if target_idx != -1:
            lines.insert(target_idx + 1, new_task_line)
        else:
            lines.append(f"\n## ✅ 오늘 완료한 일 (Completed GTD Tasks)\n{new_task_line}")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)
            logger.info(f"Surgically transferred completed task to daily log {filepath}: {clean_task}")
            return True
        except OSError as e:
            logger.error(f"Failed to write transferred task to {filepath}: {e}")
            return False

    def read_daily_log(self, date_obj: datetime | None = None) -> str:
        """
        지정된 날짜(기본값: 오늘, KST)의 일일 로그 마크다운 파일(logs/daily/YYYY-MM-DD.md)을 읽어
        전문 및 메타데이터를 반환합니다 (ADR-022).
        """
        date_obj = self.normalize_datetime(date_obj)
        date_str = date_obj.strftime("%Y-%m-%d")
        filepath = self.get_lifelog_filepath(date_obj)
        rel_path = os.path.relpath(filepath, self.base_dir)

        if not os.path.exists(filepath):
            return (
                f"ℹ️ **오늘({date_str}) 작성된 일일 로그가 아직 없습니다.**\n\n"
                f"* **대상 파일**: `{rel_path}`\n"
                f"* 일과나 생각, 메모를 남겨주시면 즉시 마크다운에 기록하고 Git에 반영해 드립니다! ✍️"
            )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()

            mtime = datetime.fromtimestamp(os.path.getmtime(filepath), tz=get_app_timezone()).strftime("%H:%M:%S")
            lines_count = len(content.splitlines())

            return (
                f"### 📅 오늘 일일 로그 (`{date_str}`)\n\n"
                f"* **파일 경로**: `{rel_path}` (최종 수정: `{mtime}`, 총 `{lines_count}`줄)\n\n"
                f"---\n\n"
                f"{content}\n"
            )
        except OSError as e:
            logger.error(f"Failed to read daily log at {filepath}: {e}")
            return f"⚠️ 일일 로그 파일 읽기 오류: {e}"
