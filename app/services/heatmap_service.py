"""Heatmap & Lifelog In-Place Editor Service (ADR-045).

GitHub 스타일 연간/월간 잔디(Contribution Heatmap) 데이터 집계 및
마크다운 일일 로그 인플레이스 편집/저장 파이프라인을 제공합니다.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any

from app.config import get_app_timezone, get_now
from app.services.agent_service import AgentService
from app.services.git_service import GitService

logger = logging.getLogger("watson.heatmap")


class HeatmapService:
    """연간/월간 잔디(Contribution Heatmap) 데이터 수집 및 마크다운 일일 로그 인플레이스 편집기 서비스."""

    def __init__(self, base_dir: str | None = None) -> None:
        if base_dir:
            self.base_dir = os.path.abspath(os.path.expanduser(base_dir))
        else:
            from app.services.settings_service import SettingsService
            self.base_dir = SettingsService().get_gtd_path()
        self.agent_service = AgentService(base_dir=self.base_dir)
        self.git_service = GitService(repo_path=self.base_dir)

    def _normalize_date(self, date_val: date | datetime | str | None = None) -> date:
        if date_val is None:
            return get_now().date()
        if isinstance(date_val, datetime):
            return date_val.date()
        if isinstance(date_val, str):
            try:
                return datetime.strptime(date_val.strip(), "%Y-%m-%d").replace(tzinfo=get_app_timezone()).date()
            except ValueError:
                return get_now().date()
        return date_val

    def scan_all_daily_logs(self) -> dict[str, dict[str, Any]]:
        """
        저장소 내 모든 일일 로그 파일(logs/daily/*.md 및 lifelogs/YYYY/MM/*.md)을 스캔하여
        날짜(YYYY-MM-DD)별 통계 딕셔너리를 반환합니다.
        """
        results: dict[str, dict[str, Any]] = {}
        date_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")

        search_dirs: list[str] = []
        daily_dir = os.path.join(self.base_dir, "logs", "daily")
        if os.path.exists(daily_dir):
            search_dirs.append(daily_dir)

        lifelog_root = os.path.join(self.base_dir, "lifelogs")
        if os.path.exists(lifelog_root):
            for root, _, files in os.walk(lifelog_root):
                if any(f.endswith(".md") for f in files):
                    search_dirs.append(root)

        for s_dir in search_dirs:
            try:
                for fname in os.listdir(s_dir):
                    match = date_pattern.match(fname)
                    if not match:
                        continue
                    date_str = match.group(1)
                    filepath = os.path.join(s_dir, fname)
                    if not os.path.isfile(filepath):
                        continue

                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()

                        char_count = len(content.strip())
                        completed_tasks = len(re.findall(r"^[ \t]*-[ \t]+\[[xX]\]", content, re.MULTILINE))
                        pending_tasks = len(re.findall(r"^[ \t]*-[ \t]+\[[ ]\]", content, re.MULTILINE))
                        total_tasks = completed_tasks + pending_tasks

                        # 잔디 기여도 레벨 (0~4) 계산 (GitHub Contribution 표준)
                        level = 0
                        if char_count > 0:
                            if char_count < 200 and completed_tasks == 0:
                                level = 1
                            elif char_count < 600 or completed_tasks <= 1:
                                level = 2
                            elif char_count < 1200 or completed_tasks <= 3:
                                level = 3
                            else:
                                level = 4

                        results[date_str] = {
                            "date": date_str,
                            "filepath": filepath,
                            "exists": True,
                            "char_count": char_count,
                            "completed_tasks": completed_tasks,
                            "pending_tasks": pending_tasks,
                            "total_tasks": total_tasks,
                            "level": level,
                            "modified_at": os.path.getmtime(filepath),
                        }
                    except OSError as err:
                        logger.warning(f"Failed to read lifelog file {filepath}: {err}")
            except OSError as err:
                logger.warning(f"Failed to list directory {s_dir}: {err}")

        return results

    def get_heatmap_data(self, days: int = 365, end_date: date | None = None) -> dict[str, Any]:
        """
        지정된 기간(기본값: 최근 365일, KST)에 대한 연속 날짜별 잔디 메트릭 및 요약 통계를 반환합니다.
        """
        end_d = self._normalize_date(end_date)
        start_d = end_d - timedelta(days=days - 1)

        scanned_logs = self.scan_all_daily_logs()

        days_list: list[dict[str, Any]] = []
        total_days_logged = 0
        total_completed_tasks = 0
        total_chars = 0

        curr_d = start_d
        while curr_d <= end_d:
            d_str = curr_d.strftime("%Y-%m-%d")
            weekday_idx = curr_d.weekday()  # 0=월 ~ 6=일

            log_info = scanned_logs.get(d_str)
            if log_info:
                total_days_logged += 1
                total_completed_tasks += log_info["completed_tasks"]
                total_chars += log_info["char_count"]
                days_list.append({
                    "date": d_str,
                    "weekday": weekday_idx,
                    "exists": True,
                    "char_count": log_info["char_count"],
                    "completed_tasks": log_info["completed_tasks"],
                    "total_tasks": log_info["total_tasks"],
                    "level": log_info["level"],
                })
            else:
                days_list.append({
                    "date": d_str,
                    "weekday": weekday_idx,
                    "exists": False,
                    "char_count": 0,
                    "completed_tasks": 0,
                    "total_tasks": 0,
                    "level": 0,
                })
            curr_d += timedelta(days=1)

        # 연속 기록 일수 (Streak) 계산
        # 오늘부터 과거로 역추적 (오늘 미작성인 경우 어제부터 체크)
        current_streak = 0
        check_d = end_d
        today_str = check_d.strftime("%Y-%m-%d")
        if today_str not in scanned_logs:
            check_d = check_d - timedelta(days=1)

        while check_d >= start_d:
            c_str = check_d.strftime("%Y-%m-%d")
            if c_str in scanned_logs and scanned_logs[c_str]["char_count"] > 0:
                current_streak += 1
                check_d -= timedelta(days=1)
            else:
                break

        # 최장 연속 기록 일수 (Longest Streak)
        longest_streak = 0
        running_streak = 0
        for item in days_list:
            if item["exists"] and item["char_count"] > 0:
                running_streak += 1
                longest_streak = max(longest_streak, running_streak)
            else:
                running_streak = 0

        completion_rate = round((total_days_logged / days) * 100, 1) if days > 0 else 0.0

        summary = {
            "total_days_logged": total_days_logged,
            "total_completed_tasks": total_completed_tasks,
            "total_chars": total_chars,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "completion_rate": completion_rate,
            "range_days": days,
            "start_date": start_d.strftime("%Y-%m-%d"),
            "end_date": end_d.strftime("%Y-%m-%d"),
        }

        return {
            "summary": summary,
            "days": days_list,
        }

    def get_lifelog_content(self, date_str: str) -> dict[str, Any]:
        """
        지정된 일자의 마크다운 일일 로그 원문과 파일 정보를 반환합니다.
        파일이 없는 경우 표준 기본 템플릿 초안을 생성하여 반환합니다.
        """
        date_obj = self._normalize_date(date_str)
        normalized_date_str = date_obj.strftime("%Y-%m-%d")

        # 대상 파일 경로 획득
        filepath = self.agent_service.get_lifelog_filepath(
            datetime.combine(date_obj, datetime.min.time(), tzinfo=get_app_timezone())
        )

        exists = os.path.exists(filepath)
        content = ""
        if exists:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError as err:
                logger.error(f"Failed to read lifelog file {filepath}: {err}")
                content = f"# {normalized_date_str}\n\n*(파일 읽기 실패: {err})*"
        else:
            # 초기 마크다운 템플릿 생성
            content = (
                f"# {normalized_date_str}\n\n"
                f"## 📝 오늘 하루 일상 및 기록 (Daily Journal)\n\n"
                f"## 📅 주요 일정 (Schedule)\n\n"
                f"## ✅ 오늘 완료한 일 (Completed GTD Tasks)\n\n"
                f"## 💡 순간 메모 / 캡처 (Capture)\n"
            )

        completed_tasks = len(re.findall(r"^[ \t]*-[ \t]+\[[xX]\]", content, re.MULTILINE))
        pending_tasks = len(re.findall(r"^[ \t]*-[ \t]+\[[ ]\]", content, re.MULTILINE))

        return {
            "exists": exists,
            "date": normalized_date_str,
            "filepath": filepath,
            "content": content,
            "char_count": len(content),
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "last_modified": os.path.getmtime(filepath) if exists else None,
        }

    def save_lifelog_content(
        self,
        date_str: str,
        content: str,
        commit_msg: str | None = None,
        auto_push: bool = True,
    ) -> dict[str, Any]:
        """
        특정 일자의 일일 로그 내용을 물리적 디스크에 저장하고,
        1기록 1커밋 정책에 따라 Git 커밋 및 선택적 원격 푸시를 집행합니다 (ADR-045).
        """
        if not date_str or not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str.strip()):
            return {
                "success": False,
                "error": f"유효하지 않은 날짜 형식입니다: '{date_str}' (YYYY-MM-DD 형식 필요)",
            }

        date_obj = self._normalize_date(date_str)
        normalized_date_str = date_obj.strftime("%Y-%m-%d")

        filepath = self.agent_service.get_lifelog_filepath(
            datetime.combine(date_obj, datetime.min.time(), tzinfo=get_app_timezone())
        )

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as err:
            logger.error(f"Failed to save lifelog file {filepath}: {err}")
            return {
                "success": False,
                "error": f"파일 저장 실패: {err}",
                "date": normalized_date_str,
                "filepath": filepath,
            }

        # Git 커밋 집행
        msg = commit_msg or f"docs(log): {normalized_date_str} 일일 로그 수동 편집 및 갱신"
        committed, commit_res_msg = self.git_service.commit(commit_message=msg)

        pushed = False
        push_msg = ""
        if auto_push and committed:
            push_success, push_msg = self.git_service.push()
            pushed = push_success

        return {
            "success": True,
            "date": normalized_date_str,
            "filepath": filepath,
            "char_count": len(content),
            "committed": committed,
            "commit_message": msg,
            "commit_result": commit_res_msg,
            "pushed": pushed,
            "push_message": push_msg,
        }

    def format_edit_card(self, date_str: str, base_url: str = "") -> str:
        """
        텔레그램 및 DevBot 콘솔에 전달할 일일 로그 인플레이스 편집기 안내 카드 마크다운을 생성합니다.
        """
        info = self.get_lifelog_content(date_str)
        d_str = info["date"]
        exists = info["exists"]
        char_count = info["char_count"]
        completed = info["completed_tasks"]

        status_badge = f"✅ 작성됨 ({char_count:,}자, 완료 태스크 {completed}개)" if exists else "📝 미작성 (새로 작성)"
        web_link = f"{base_url.rstrip('/')}/watson?edit={d_str}" if base_url else f"/?edit={d_str}"

        lines = [
            f"### ✏️ **Watson 일일 로그 인플레이스 편집기** (`{d_str}`) 📝",
            f"• **작성 상태**: {status_badge}",
            f"• **저장 경로**: `{info['filepath']}`",
            "",
            "#### 🌐 **웹 분할 에디터 바로가기**",
            f"• [👉 웹 대시보드에서 '{d_str}' 로그 편집 열기]({web_link})",
            "",
            "*(웹 대시보드에서 좌우 분할 에디터로 실시간 마크다운 편집 및 원터치 Git 커밋/푸시가 가능합니다)* 🚀✨",
        ]

        if exists and char_count > 0:
            lines.append("")
            lines.append("#### 📄 **현재 로그 내용 요약 (앞 300자)**")
            preview = info["content"].strip()[:300]
            lines.append(f"```markdown\n{preview}\n...```")

        return "\n".join(lines)
