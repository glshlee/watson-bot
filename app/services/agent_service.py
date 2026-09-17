from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from app.services.gtd_service import GTDService
from app.services.lifelog_service import LifelogService

logger = logging.getLogger("watson.agent")

__all__ = ["AgentService", "GTDService", "LifelogService"]


class AgentService:
    """
    마크다운 라이프로그 및 GTD 오케스트레이션 서비스 파사드 (ADR-001, ADR-007, ADR-053).
    단일 책임 원칙(SRP)에 따라 분리된 LifelogService와 GTDService를 오케스트레이션하며,
    기존 호출자 및 테스트에 대한 100% 하위 호환성을 보장합니다.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(os.path.expanduser(base_dir))
        self.lifelog_service = LifelogService(base_dir=self.base_dir)
        self.gtd_service = GTDService(base_dir=self.base_dir, lifelog_service=self.lifelog_service)
        self.lifelog_service.set_gtd_service(self.gtd_service)

    def has_gtd_inbox(self) -> bool:
        """GTD 수집함(inbox.md) 파일 존재 여부 확인"""
        return self.gtd_service.has_gtd_inbox()

    def has_daily_logs_structure(self) -> bool:
        """logs/daily 폴더 구조 존재 여부 확인"""
        return self.lifelog_service.has_daily_logs_structure()

    def get_gtd_inbox_filepath(self) -> str:
        """GTD inbox 파일 경로 반환 (우선순위: gtd/inbox.md -> inbox.md)"""
        return self.gtd_service.get_gtd_inbox_filepath()

    def append_to_gtd_inbox(self, content: str) -> str:
        """GTD Inbox(수집함)의 맞춤형 섹션에 할 일/메모를 추가합니다."""
        return self.gtd_service.append_to_gtd_inbox(content)

    def _normalize_datetime(self, date_obj: datetime | None = None) -> datetime:
        """입력된 date_obj를 애플리케이션 설정 타임존(KST)으로 정규화합니다."""
        return self.lifelog_service.normalize_datetime(date_obj)

    def get_lifelog_filepath(self, date_obj: datetime | None = None) -> str:
        """일일 로그 마크다운 파일 절대 경로를 반환합니다."""
        return self.lifelog_service.get_lifelog_filepath(date_obj)

    def append_or_update_lifelog(
        self,
        content: str,
        category: str = "Daily Notes & Diary",
        date_obj: datetime | None = None,
    ) -> str:
        """일상 메모 및 라이프로그를 마크다운에 기록하거나 GTD 인박스로 라우팅합니다."""
        return self.lifelog_service.append_or_update_lifelog(content=content, category=category, date_obj=date_obj)

    def get_gtd_summary(self, date_obj: datetime | None = None) -> str:
        """오늘의 일정, Next Actions, Inbox 항목을 종합 추출하여 비서 브리핑을 생성합니다."""
        return self.gtd_service.get_gtd_summary(date_obj)

    def remove_gtd_tasks(self, keywords: list[str]) -> list[str]:
        """gtd/inbox.md 및 gtd/next_actions.md에서 주어진 키워드 태스크 라인을 제거합니다."""
        return self.gtd_service.remove_gtd_tasks(keywords)

    def find_and_remove_matching_tasks(self, user_message: str) -> list[str]:
        """사용자 메시지에서 삭제 의도를 감지하여 일치하는 태스크를 안전하게 제거합니다."""
        return self.gtd_service.find_and_remove_matching_tasks(user_message)

    def transfer_completed_task_to_daily_log(
        self,
        task_text: str,
        date_obj: datetime | None = None,
    ) -> bool:
        """완료된 GTD 태스크를 당일 데일리 로그로 수술적 이관(Surgical Transfer)합니다."""
        return self.lifelog_service.transfer_completed_task_to_daily_log(task_text, date_obj)

    def complete_top_task(self) -> dict[str, Any]:
        """첫 번째 미완료 태스크를 찾아 완료 처리하고 당일 데일리 로그로 이관합니다."""
        return self.gtd_service.complete_top_task()

    def complete_matching_tasks(self, keywords: list[str]) -> list[str]:
        """키워드와 일치하는 미완료 태스크들을 찾아 완료 처리하고 데일리 로그로 이관합니다."""
        return self.gtd_service.complete_matching_tasks(keywords)

    def read_daily_log(self, date_obj: datetime | None = None) -> str:
        """지정된 날짜의 일일 로그 마크다운 파일을 읽어 전문 및 메타데이터를 반환합니다."""
        return self.lifelog_service.read_daily_log(date_obj)

    def read_gtd_files(self) -> str:
        """수집함(inbox.md) 및 다음 행동(next_actions.md) 파일을 직접 읽어 현황을 반환합니다."""
        return self.gtd_service.read_gtd_files()

    def read_gtd_and_daily_log(self, date_obj: datetime | None = None) -> str:
        """오늘자 일일 로그와 GTD 파일 현황을 종합 브리핑합니다."""
        log_text = self.read_daily_log(date_obj)
        gtd_text = self.read_gtd_files()
        return f"{log_text}\n\n---\n\n{gtd_text}"
