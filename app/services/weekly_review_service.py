import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, ClassVar

from app.config import get_now

logger = logging.getLogger("watson.weekly_review")


class WeeklyReviewService:
    """
    주간 결산 회고(Weekly Review) 리포트 생성 및 통계 집계 서비스 (ADR-043).
    
    지난 7일간의 일일 로그(logs/daily/YYYY-MM-DD.md)를 파싱하여:
    - 📝 기록 달성률 (N일 / 7일)
    - ✅ 완료한 GTD 태스크 (- [x]) 전수 집계
    - 📈 카테고리별 활동(운동, 업무, 생각/아이디어, 생활) 집계
    - 📥 GTD 수집함(Inbox) 장기 체류 점검 및 정리 가이드
    - 💬 왓슨의 따뜻한 주간 회고 한마디(AI 및 룰 기반 하이브리드)
    를 제공합니다.
    """

    WEEKDAYS_KO: ClassVar[list[str]] = ["월", "화", "수", "목", "금", "토", "일"]

    def __init__(self, base_dir: str = ".", llm_provider: Any | None = None):
        self.base_dir = os.path.abspath(os.path.expanduser(base_dir))
        self.llm_provider = llm_provider

    def collect_weekly_data(
        self,
        ref_date: datetime | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        """
        기준일(ref_date)로부터 과거 N일간의 라이프로그 및 GTD 현황 데이터를 수집합니다.
        """
        now_dt = ref_date or get_now()
        end_date = now_dt.date()
        start_date = end_date - timedelta(days=max(1, days) - 1)

        daily_dir = os.path.join(self.base_dir, "logs", "daily")

        recorded_days = 0
        recorded_dates: list[str] = []
        completed_tasks: list[dict[str, str]] = []

        workout_events: list[str] = []
        work_events: list[str] = []
        idea_events: list[str] = []
        life_events: list[str] = []

        workout_keywords = ["러닝", "헬스", "스쿼트", "푸시업", "운동", "수영", "사이클", "산책", "스트레칭", "인바디", "workout", "gym"]
        work_keywords = ["회의", "개발", "배포", "기획", "보고", "아키텍처", "테스트", "리팩토링", "pr", "커밋", "work", "databricks"]

        curr_date = start_date
        while curr_date <= end_date:
            date_str = curr_date.strftime("%Y-%m-%d")
            fpath = os.path.join(daily_dir, f"{date_str}.md")

            if os.path.exists(fpath):
                recorded_days += 1
                weekday_ko = self.WEEKDAYS_KO[curr_date.weekday()]
                recorded_dates.append(f"{date_str} ({weekday_ko})")

                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Error reading {fpath}: {e}")
                    lines = []

                current_section = ""
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue

                    if stripped.startswith("#"):
                        current_section = stripped.lstrip("#").strip().lower()
                        continue

                    # 1. 완료 태스크 추출 (- [x])
                    if stripped.startswith(("- [x]", "- [X]")):
                        task_text = re.sub(r"^-\s*\[[xX]\]\s*", "", stripped).strip()
                        if task_text:
                            completed_tasks.append({
                                "date": date_str,
                                "weekday": weekday_ko,
                                "task": task_text,
                            })

                    # 2. 카테고리별 활동 탐색
                    line_lower = stripped.lower()
                    if "운동" in current_section:
                        workout_events.append(f"[{date_str}] {stripped}")
                    elif "아이디어" in current_section or "캡처" in current_section or "메모" in current_section:
                        idea_events.append(f"[{date_str}] {stripped}")
                    elif "업무" in current_section or "회사" in current_section:
                        work_events.append(f"[{date_str}] {stripped}")
                    elif "일상" in current_section or "일기" in current_section:
                        life_events.append(f"[{date_str}] {stripped}")
                    elif any(k in line_lower for k in workout_keywords):
                        workout_events.append(f"[{date_str}] {stripped}")
                    elif any(k in line_lower for k in work_keywords):
                        work_events.append(f"[{date_str}] {stripped}")
                    else:
                        life_events.append(f"[{date_str}] {stripped}")

            curr_date += timedelta(days=1)

        # 3. GTD Inbox 미분류 항목 수집
        inbox_candidates = [
            os.path.join(self.base_dir, "gtd", "inbox.md"),
            os.path.join(self.base_dir, "inbox.md"),
        ]
        inbox_items: list[str] = []
        for ipath in inbox_candidates:
            if os.path.exists(ipath):
                try:
                    with open(ipath, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            sline = line.strip()
                            if sline.startswith("- [ ]"):
                                item_text = re.sub(r"^-\s*\[\s*\]\s*", "", sline).strip()
                                # 캡처 배지 및 불필요 접미사 정리
                                item_text = re.sub(r"\*\(Watson\s*캡처\)\*", "", item_text).strip()
                                if item_text and item_text not in inbox_items:
                                    inbox_items.append(item_text)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Error reading inbox {ipath}: {e}")
                break

        total_days = max(1, days)
        record_rate = round((recorded_days / total_days) * 100)

        start_weekday = self.WEEKDAYS_KO[start_date.weekday()]
        end_weekday = self.WEEKDAYS_KO[end_date.weekday()]

        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "start_weekday": start_weekday,
            "end_date": end_date.strftime("%Y-%m-%d"),
            "end_weekday": end_weekday,
            "total_days": total_days,
            "recorded_days": recorded_days,
            "record_rate": record_rate,
            "recorded_dates": recorded_dates,
            "completed_tasks": completed_tasks,
            "total_completed": len(completed_tasks),
            "categories": {
                "workout_count": len(workout_events),
                "work_count": len(work_events),
                "idea_count": len(idea_events),
                "life_count": len(life_events),
            },
            "inbox_items": inbox_items,
            "inbox_pending_count": len(inbox_items),
        }

    def _generate_rule_based_commentary(self, data: dict[str, Any]) -> str:
        """규칙 기반의 맞춤형 주간 한마디 총평 생성 (안전 폴백)."""
        rate = data.get("record_rate", 0)
        completed = data.get("total_completed", 0)
        workout = data.get("categories", {}).get("workout_count", 0)

        comments = []
        if rate >= 80:
            comments.append("이번 주는 거의 매일 기록을 남기며 일상을 꼼꼼히 가꾸셨네요! ✨")
        elif rate >= 50:
            comments.append("바쁜 일상 속에서도 소중한 순간들을 잊지 않고 꾸준히 기록하셨습니다. 👍")
        else:
            comments.append("기록이 조금 뜸했지만, 언제든 다시 왓슨에게 편하게 들려주세요. 😊")

        if completed > 0:
            comments.append(f"총 {completed}개의 GTD 과제를 해결하며 착실한 진전을 이루어냈습니다.")
        else:
            comments.append("다음 주에는 작은 태스크부터 하나씩 완료해보는 것도 좋겠습니다.")

        if workout > 0:
            comments.append("건강과 체력을 돌보는 운동도 잊지 않으셨네요! 🏃")

        comments.append("수고 많으셨던 이번 한 주를 잘 마무리하시고, 다음 주도 힘차게 시작해봐요! 👏")
        return " ".join(comments)

    def generate_weekly_review(
        self,
        ref_date: datetime | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        """
        주간 결산 리포트 전체를 생성하여 마크다운 및 메트릭스 딕셔너리로 반환합니다.
        """
        data = self.collect_weekly_data(ref_date=ref_date, days=days)

        start_str = f"{data['start_date']} ({data['start_weekday']})"
        end_str = f"{data['end_date']} ({data['end_weekday']})"
        total_days = data["total_days"]
        rec_days = data["recorded_days"]
        rec_rate = data["record_rate"]
        completed_tasks = data["completed_tasks"]
        inbox_items = data["inbox_items"]
        inbox_count = data["inbox_pending_count"]
        cats = data["categories"]

        # AI 총평 합성 시도 (LLM 사용 가능 시)
        ai_commentary = ""
        if self.llm_provider and hasattr(self.llm_provider, "generate_completion"):
            try:
                task_samples = [f"- {t['task']}" for t in completed_tasks[:4]]
                prompt = (
                    f"사용자의 지난 {total_days}일간 라이프로그 통계입니다:\n"
                    f"- 기록 일수: {rec_days}/{total_days}일 ({rec_rate}%)\n"
                    f"- 완료한 과제 수: {len(completed_tasks)}개\n"
                    f"- 주요 완료 과제: {', '.join(task_samples) if task_samples else '없음'}\n"
                    f"- 운동 활동: {cats['workout_count']}회, 업무 집중: {cats['work_count']}회\n\n"
                    f"사용자에게 따뜻하고 지혜로운 비서(왓슨)의 톤으로 한 주를 돌아보고 격려하는 총평(2~3문장, 존댓말, 이모지 포함)을 작성해주세요."
                )
                res = self.llm_provider.generate_completion(prompt)
                if res and len(res.strip()) > 10:
                    ai_commentary = res.strip()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"AI weekly commentary generation failed: {e}")

        if not ai_commentary:
            ai_commentary = self._generate_rule_based_commentary(data)

        # 마크다운 리포트 카드 빌드
        lines = [
            "📊 **[왓슨 주간 결산 리포트 (Weekly Review)]**",
            f"*기간: {start_str} ~ {end_str} ({total_days}일간)*\n",
            "### 🏆 이번 주 주요 성과 (Highlights)",
            f"• 📝 **기록 달성률**: 총 {total_days}일 중 **{rec_days}일** 기록 완료 ({rec_rate}%)",
            f"• ✅ **완료한 GTD 태스크**: 총 **{len(completed_tasks)}개** 완료",
        ]

        if completed_tasks:
            for ct in completed_tasks[:5]:
                lines.append(f"  - [{ct['date'][-5:]}] {ct['task']}")
            if len(completed_tasks) > 5:
                lines.append(f"  - *...외 {len(completed_tasks) - 5}건 추가 완료*")
        else:
            lines.append("  - *(이번 주 완료된 태스크가 없습니다)*")

        lines.append("")
        lines.append("### 📈 카테고리별 활동 현황")
        lines.append(f"• 🏃 **운동 & 건강**: {cats['workout_count']}건 활동 실천")
        lines.append(f"• 💻 **업무 & 프로젝트**: {cats['work_count']}건 몰입")
        lines.append(f"• 💡 **생각 & 메모**: {cats['idea_count']}건 캡처")

        lines.append("")
        lines.append("### 📥 GTD 수집함(Inbox) 점검 가이드")
        if inbox_count > 0:
            lines.append(f"현재 수집함에 정리 대기 중인 항목이 **{inbox_count}개** 있습니다:")
            for item in inbox_items[:4]:
                lines.append(f"• `{item}`")
            if inbox_count > 4:
                lines.append(f"• *...외 {inbox_count - 4}개 대기 중*")
            lines.append("👉 *주말 동안 `next_actions.md`로 실행 과제를 배치하거나 정리해 보세요!*")
        else:
            lines.append("현재 수집함에 밀린 항목 없이 깨끗하게 비워져 있습니다! ✨")

        lines.append("")
        lines.append("### 💬 왓슨의 주간 한마디")
        lines.append(f"> \"{ai_commentary}\"")

        lines.append("\n---")
        lines.append("💡 *지난 기록 검색은 `/search [키워드]`, 특정 일자 확인은 `/today YYYY-MM-DD`를 이용하세요.*")

        report_markdown = "\n".join(lines)

        return {
            "metrics": data,
            "markdown": report_markdown,
            "commentary": ai_commentary,
        }
