import logging
import os
import re
from datetime import datetime
from typing import Any

from app.config import get_now
from app.services.agent_service import AgentService
from app.services.git_service import GitService
from app.services.llm_provider import LLMProvider
from app.services.settings_service import SettingsService

logger = logging.getLogger("watson.briefing")

WEEKDAYS_KR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


class BriefingService:
    """
    아침 및 저녁 맞춤형 GTD 브리핑 생성 서비스 (ADR-024).
    - 시간대(KST) 및 명시적 인자에 따른 Morning / Evening 모드 자동 감지
    - GTD 수집함(inbox.md), 다음 행동(next_actions.md), 당일 데일리 로그 수집
    - 지능형 LLM 브리핑 합성 및 결정론적 룰 기반 폴백 듀얼 엔진
    """

    def __init__(
        self,
        base_dir: str | None = None,
        llm_provider: LLMProvider | None = None,
        git_service: GitService | None = None,
    ):
        self.settings_service = SettingsService()
        self.base_dir = base_dir or self.settings_service.get_gtd_path()
        self.agent_service = AgentService(base_dir=self.base_dir)
        self.llm_provider = llm_provider or LLMProvider()
        self.git_service = git_service or GitService(repo_path=self.base_dir)

    def detect_briefing_mode(self, override_mode: str | None = None, date_obj: datetime | None = None) -> str:
        """
        브리핑 모드(morning 또는 evening)를 결정합니다.
        명시적 모드가 지정된 경우 이를 따르고, 미지정 시 한국 표준시(KST) 기준
        오전 05:00 ~ 13:59는 morning, 그 외(14:00 이후 및 야간)는 evening을 자동 판별합니다.
        """
        if override_mode:
            m_lower = override_mode.strip().lower()
            if any(k in m_lower for k in ["morning", "am", "아침", "출근", "모닝", "시작"]):
                return "morning"
            if any(k in m_lower for k in ["evening", "pm", "저녁", "퇴근", "회고", "정산", "이브닝", "마무리"]):
                return "evening"

        now_dt = date_obj or get_now()
        current_hour = now_dt.hour
        return "morning" if 5 <= current_hour < 14 else "evening"

    def read_briefing_context(self, date_obj: datetime | None = None) -> dict[str, Any]:
        """
        GTD 파일(inbox.md, next_actions.md) 및 당일 일일 로그 파일에서 브리핑에 필요한 데이터를 수집 및 분석합니다.
        """
        now_dt = date_obj or get_now()
        date_str = now_dt.strftime("%Y-%m-%d")
        weekday_str = WEEKDAYS_KR[now_dt.weekday()]

        schedule_items: list[str] = []
        completed_items: list[str] = []
        daily_notes: list[str] = []
        next_actions: list[str] = []
        inbox_items: list[str] = []

        raw_inbox = ""
        raw_next_actions = ""
        raw_daily_log = ""

        # 1. 일일 로그 읽기
        daily_path = self.agent_service.get_lifelog_filepath(now_dt)
        if not os.path.exists(daily_path) and self.agent_service.has_daily_logs_structure():
            daily_dir = os.path.join(self.base_dir, "logs", "daily")
            if os.path.exists(daily_dir):
                files = sorted([f for f in os.listdir(daily_dir) if f.endswith(".md")], reverse=True)
                if files:
                    daily_path = os.path.join(daily_dir, files[0])

        if os.path.exists(daily_path):
            try:
                with open(daily_path, "r", encoding="utf-8") as f:
                    raw_daily_log = f.read(2000)

                lines = raw_daily_log.splitlines()
                current_section = ""
                for line in lines:
                    line_s = line.strip()
                    if line_s.startswith("## "):
                        current_section = line_s.lower()
                        continue
                    if line_s.startswith(("- [ ]", "- [x]", "- [X]", "- [", "- ")):
                        content = re.sub(r"^-\s*(\[[ xX]\]\s*)?", "", line_s).strip()
                        if not content or content.startswith("("):
                            continue
                        if "일정" in current_section or "schedule" in current_section:
                            schedule_items.append(content)
                        elif "완료" in current_section or "complete" in current_section or line_s.startswith(("- [x]", "- [X]")):
                            completed_items.append(content)
                        else:
                            daily_notes.append(content)
            except OSError as e:
                logger.warning(f"Failed to read daily log at {daily_path}: {e}")

        # 2. Next Actions 읽기
        next_actions_path = os.path.join(self.base_dir, "gtd", "next_actions.md")
        if os.path.exists(next_actions_path):
            try:
                with open(next_actions_path, "r", encoding="utf-8") as f:
                    raw_next_actions = f.read(2500)
                for line in raw_next_actions.splitlines():
                    line_s = line.strip()
                    if line_s.startswith("- [ ]"):
                        item = line_s[5:].strip()
                        if item and not item.startswith("("):
                            next_actions.append(item)
                    elif line_s.startswith(("- [x]", "- [X]")):
                        item = line_s[5:].strip()
                        if item and not item.startswith("("):
                            completed_items.append(item)
            except OSError as e:
                logger.warning(f"Failed to read next_actions.md: {e}")

        # 3. GTD Inbox 읽기
        inbox_path = self.agent_service.get_gtd_inbox_filepath()
        if os.path.exists(inbox_path):
            try:
                with open(inbox_path, "r", encoding="utf-8") as f:
                    raw_inbox = f.read(2000)
                for line in raw_inbox.splitlines():
                    line_s = line.strip()
                    if line_s.startswith("- [ ]"):
                        item = line_s[5:].strip()
                        if item and not item.startswith("("):
                            inbox_items.append(item)
            except OSError as e:
                logger.warning(f"Failed to read inbox.md: {e}")

        return {
            "date_str": date_str,
            "weekday_str": weekday_str,
            "schedule_items": schedule_items,
            "completed_items": list(dict.fromkeys(completed_items)),
            "daily_notes": daily_notes,
            "next_actions": next_actions,
            "inbox_items": inbox_items,
            "raw_inbox": raw_inbox[:1500],
            "raw_next_actions": raw_next_actions[:2000],
            "raw_daily_log": raw_daily_log[:1500],
        }

    def _generate_rule_based_briefing(self, mode: str, date_obj: datetime, context: dict[str, Any]) -> str:
        """
        네트워크 또는 LLM 지연 없이 0.01초 내에 안전하게 응답하는 결정론적 룰 기반 브리핑 마크다운을 생성합니다.
        """
        date_str = context["date_str"]
        weekday_str = context["weekday_str"]
        next_actions = context["next_actions"]
        inbox_items = context["inbox_items"]
        schedule_items = context["schedule_items"]
        completed_items = context["completed_items"]

        if mode == "morning":
            urgent = [a for a in next_actions if any(k in a for k in ["🚨", "오늘", "마감", "중요", "긴급", "P1"])]
            normal = [a for a in next_actions if a not in urgent]
            ordered_actions = urgent + normal
            top_3 = ordered_actions[:3]

            lines = [
                f"### 🌅 **Watson Morning Briefing** (`{date_str} {weekday_str}`) ☀️\n",
                "활기찬 아침입니다! 오늘 하루 집중해야 할 핵심 우선순위와 일정을 정리해 드립니다.\n",
            ]

            lines.append("#### 🎯 **오늘의 집중 우선순위 Top 3**")
            if top_3:
                for idx, act in enumerate(top_3, 1):
                    lines.append(f"{idx}. {act}")
            else:
                lines.append("1. 오늘 등록된 최우선 과제가 없습니다. 자유롭게 하루를 설계해 보세요.")
            lines.append("")

            lines.append("#### ⏰ **추천 실행 순서 (Schedule & Flow)**")
            if schedule_items:
                lines.append(f"* **📅 확정 일정**: {', '.join(schedule_items[:3])}")
            if top_3:
                lines.append(f"* **오전 집중 (Deep Work)**: `{top_3[0]}` 완료 집중")
                if len(top_3) > 1:
                    lines.append(f"* **오후 추진 (Actions)**: `{', '.join(top_3[1:])}` 순차 처리")
            else:
                lines.append("* **오전/오후**: 중요한 생각 정리 및 가벼운 일과 진행")
            lines.append("")

            lines.append("#### 📥 **수집함 정리 안내 (Inbox)**")
            if inbox_items:
                lines.append(f"* 미분류 수집함에 **{len(inbox_items)}개**의 항목이 대기 중입니다:")
                for item in inbox_items[:3]:
                    lines.append(f"  * `{item}`")
                if len(inbox_items) > 3:
                    lines.append(f"  * *(외 {len(inbox_items) - 3}개 더 있음)*")
                lines.append("* 여유가 되실 때 `/gtd`로 확인하시거나 다음 행동으로 구체화해 보세요.")
            else:
                lines.append("* 수집함(Inbox)이 말끔하게 비워져 있습니다. 가벼운 마음으로 출발하세요! ☕")
            lines.append("")

            lines.append("💪 오늘도 보람찬 하루 되실 수 있도록 왓슨이 곁에서 든든히 서포트하겠습니다! 무엇부터 시작할까요? ✨")
            return "\n".join(lines)

        else:
            lines = [
                f"### 🌇 **Watson Evening Briefing & 일과 회고** (`{date_str} {weekday_str}`) 🌙\n",
                "오늘 하루도 정말 고생 많으셨습니다! 오늘 달성한 성과를 돌아보고 내일을 준비합니다.\n",
            ]

            lines.append("#### ✅ **오늘 완료된 작업 하이라이트**")
            if completed_items:
                for item in completed_items[:5]:
                    lines.append(f"* {item}")
            else:
                lines.append("* 데일리 로그에 기록된 완료 작업이 없습니다. 일과 중 완료된 일이 있다면 말씀해 주세요!")
            lines.append("")

            lines.append("#### ⏳ **미완료 / 진행 중 과제 현황 (Rollover Check)**")
            if next_actions:
                lines.append(f"* 현재 **{len(next_actions)}개**의 다음 행동 과제가 남아 있습니다:")
                for act in next_actions[:4]:
                    lines.append(f"  * ▫️ {act}")
                if len(next_actions) > 4:
                    lines.append(f"  * *(외 {len(next_actions) - 4}개 잔여)*")
                lines.append("* 오늘 완료되지 못한 과제는 내일 일정으로 자연스럽게 이월됩니다.")
            else:
                lines.append("* 모든 다음 행동(Next Actions)을 산뜻하게 완료하셨습니다! 🏆")
            lines.append("")

            lines.append("#### 🎯 **내일 아침 가장 먼저 마주할 핵심 과제 (Priority 1)**")
            tomorrow_task = next_actions[0] if next_actions else (inbox_items[0] if inbox_items else "내일의 새로운 영감 및 목표 수립")
            lines.append(f"* 👉 **`{tomorrow_task}`**")
            lines.append("")

            lines.append("✨ 편안하고 아늑한 저녁 시간 보내시길 바랍니다. 왓슨은 내일 아침에도 변함없이 준비되어 있겠습니다! 푹 쉬세요. ☕🛋️")
            return "\n".join(lines)

    def generate_briefing(
        self,
        mode: str | None = None,
        date_obj: datetime | None = None,
        use_ai: bool = True,
    ) -> dict[str, Any]:
        """
        브리핑 모드에 맞춰 최신 데이터를 수집하고 구조화된 브리핑 응답을 생성합니다.
        AI 엔진 사용 가능한 경우 LLM 요약을 시도하고, 오류/지연 시 결정론적 룰 기반 브리핑으로 100% 안전 복원합니다.
        """
        now_dt = date_obj or get_now()
        active_mode = self.detect_briefing_mode(override_mode=mode, date_obj=now_dt)
        context = self.read_briefing_context(date_obj=now_dt)

        # 1. 빠른 결정론적 룰 기반 브리핑 사전 생성 (기본값)
        rule_based_briefing = self._generate_rule_based_briefing(active_mode, now_dt, context)

        # 2. AI 엔진을 통한 맞춤형 브리핑 시도 (옵션 활성화 시)
        if use_ai and self.llm_provider:
            try:
                date_label = f"{context['date_str']} ({context['weekday_str']})"
                if active_mode == "morning":
                    prompt = (
                        f"너는 사용자의 든든한 개인 AI 비서 왓슨(Watson)이다.\n"
                        f"오늘은 {date_label}이다. 아래 GTD 참고 데이터를 바탕으로 친절하고 명쾌하게 [Morning Briefing]을 작성하라.\n\n"
                        f"[참고 데이터]\n"
                        f"- GTD Inbox:\n{context['raw_inbox'] or '(비어 있음)'}\n"
                        f"- Next Actions:\n{context['raw_next_actions'] or '(비어 있음)'}\n"
                        f"- 오늘 일정 및 메모:\n{context['raw_daily_log'] or '(기록 없음)'}\n\n"
                        f"[작성 가이드라인]\n"
                        f"1. 활기차고 차분한 어조로 오늘의 시작을 엽니다.\n"
                        f"2. '🎯 오늘의 집중 우선순위 Top 3'를 명확하게 선정하세요.\n"
                        f"3. 오전/오후 시간대별 추천 실행 순서를 간결하게 정리하세요.\n"
                        f"4. Inbox에 방치된 미분류 항목이 있다면 한두 개 정리 권유를 포함하세요.\n"
                        f"5. 마크다운 형식으로 가독성 높게 정돈하여 답변하세요.\n"
                    )
                else:
                    prompt = (
                        f"너는 사용자의 든든한 개인 AI 비서 왓슨(Watson)이다.\n"
                        f"오늘은 {date_label}이다. 아래 GTD 및 일일 로그 참고 데이터를 바탕으로 [Evening Briefing & 회고]를 작성하라.\n\n"
                        f"[참고 데이터]\n"
                        f"- 오늘자 데일리 로그:\n{context['raw_daily_log'] or '(기록 없음)'}\n"
                        f"- 잔여 Next Actions:\n{context['raw_next_actions'] or '(비어 있음)'}\n"
                        f"- GTD Inbox:\n{context['raw_inbox'] or '(비어 있음)'}\n\n"
                        f"[작성 가이드라인]\n"
                        f"1. 오늘 하루 수고한 사용자를 격려하며 하루를 정리합니다.\n"
                        f"2. '✅ 오늘 완료된 작업 하이라이트'를 요약합니다.\n"
                        f"3. '⏳ 미완료/진행 중인 과제' 중 내일로 이월하거나 Inbox로 보낼 대상을 정리합니다.\n"
                        f"4. 내일 아침 가장 먼저 마주해야 할 핵심 과제 1개를 제안하세요.\n"
                        f"5. 마크다운 형식으로 정돈하여 답변하세요.\n"
                    )

                ai_res = self.llm_provider._call_ai_engine(prompt=prompt)
                if ai_res and len(ai_res) > 80 and not any(f in ai_res for f in ["날씨", "시간", "이야기 들려주세요"]):
                    logger.info(f"Generated AI-enhanced briefing for mode={active_mode}")
                    return {
                        "mode": active_mode,
                        "date": context["date_str"],
                        "markdown": ai_res,
                    }
            except Exception as e:  # noqa: BLE001
                logger.warning(f"AI briefing generation fallback to rule-based: {e}")

        return {
            "mode": active_mode,
            "date": context["date_str"],
            "markdown": rule_based_briefing,
        }
