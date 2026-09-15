import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any

from app.config import get_now

logger = logging.getLogger("watson.due_date")

WEEKDAYS_MAP = {
    "월": 0,
    "화": 1,
    "수": 2,
    "목": 3,
    "금": 4,
    "토": 5,
    "일": 6,
}


class DueDateService:
    """
    GTD 태스크 마감일(Due Date / D-Day) 자동 감지, 계산 및 브리핑 서비스 (ADR-042).
    - 정규 태그 포맷(~YYYY-MM-DD, @due, (마감: ...)) 파싱
    - 자연어 상대 일자("오늘까지", "내일까지", "다음 주 수요일까지", "9월 20일까지") 인식 및 태그 표준화
    - D-Day 계산 및 긴급도 분류 (Overdue ⛔, Today 🚨, Urgent ⚠️ D-1~D-3, Upcoming 📅 D-N)
    - GTD 파일(inbox.md, next_actions.md) 스캔 및 아침 브리핑 D-Day 경고 섹션 포맷팅
    """

    @classmethod
    def extract_due_date_from_text(
        cls,
        text: str,
        base_date: date | datetime | None = None,
    ) -> tuple[date | None, str]:
        """
        문장 또는 태스크 텍스트에서 마감일(Due Date)을 추출하고,
        자연어 마감 표현이 발견된 경우 이를 정규화된 태그(~YYYY-MM-DD)로 변환한 정제 텍스트를 반환합니다.

        반환값: (due_date_obj or None, cleaned_or_normalized_text)
        """
        ref_date = cls._resolve_base_date(base_date)
        cleaned = text.strip()

        # 1. 명시적 태그 패턴 우선 검사
        # 1-1) ~YYYY-MM-DD 또는 ~YYYY.MM.DD 또는 ~YYYY/MM/DD
        m_tag_full = re.search(r"~(20\d{2})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b", cleaned)
        if m_tag_full:
            y, m, d = int(m_tag_full.group(1)), int(m_tag_full.group(2)), int(m_tag_full.group(3))
            try:
                target_date = date(y, m, d)
                return target_date, cleaned
            except ValueError:
                pass

        # 1-2) ~MM-DD (연도 생략 시 기준 연도 매핑)
        m_tag_short = re.search(r"~(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b", cleaned)
        if m_tag_short:
            m, d = int(m_tag_short.group(1)), int(m_tag_short.group(2))
            try:
                y = ref_date.year
                # 만약 기준 월보다 4개월 이상 이전이면 내년으로 보정
                if m < ref_date.month - 4:
                    y += 1
                target_date = date(y, m, d)
                normalized = cleaned[:m_tag_short.start()] + f"~{target_date.strftime('%Y-%m-%d')}" + cleaned[m_tag_short.end():]
                return target_date, normalized
            except ValueError:
                pass

        # 1-3) @due(YYYY-MM-DD) 또는 @due(MM-DD)
        m_due = re.search(r"@due\((20\d{2})?[-/.]?(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\)", cleaned, re.IGNORECASE)
        if m_due:
            y_str, m_str, d_str = m_due.group(1), m_due.group(2), m_due.group(3)
            y = int(y_str) if y_str else ref_date.year
            m, d = int(m_str), int(d_str)
            try:
                target_date = date(y, m, d)
                return target_date, cleaned
            except ValueError:
                pass

        # 1-4) (마감: YYYY-MM-DD) 또는 (기한: ...)
        m_paren = re.search(
            r"\((?:마감|기한|due)[:\s]*(?:(20\d{2})[-/.년\s]*)?(0?[1-9]|1[0-2])[-/.월\s]*(0?[1-9]|[12]\d|3[01])일?\)",
            cleaned,
            re.IGNORECASE,
        )
        if m_paren:
            y_str, m_str, d_str = m_paren.group(1), m_paren.group(2), m_paren.group(3)
            y = int(y_str) if y_str else ref_date.year
            m, d = int(m_str), int(d_str)
            try:
                target_date = date(y, m, d)
                return target_date, cleaned
            except ValueError:
                pass

        # 2. 한국어 자연어 마감 표현 인식 (대화형 태스크 생성 시)
        # 예: "오늘까지", "내일까지", "모레까지", "글피까지"
        m_rel_day = re.search(r"\b(오늘|내일|모레|글피)(?:까지|엔|에\s*마감|에)", cleaned)
        if m_rel_day:
            word = m_rel_day.group(1)
            offset = 0
            if word == "오늘":
                offset = 0
            elif word == "내일":
                offset = 1
            elif word == "모레":
                offset = 2
            elif word == "글피":
                offset = 3
            target_date = ref_date + timedelta(days=offset)
            # 텍스트에서 상대일자 표현 제거
            norm_text = cleaned[:m_rel_day.start()].strip() + " " + cleaned[m_rel_day.end():].strip()
            norm_text = norm_text.strip()
            return target_date, f"{norm_text} ~{target_date.strftime('%Y-%m-%d')}".strip()

        # 예: "다음 주 수요일까지", "이번 주 금요일까지", "금요일까지"
        m_weekday = re.search(
            r"\b(이번\s*주|다음\s*주|다다음\s*주)?\s*([월화수목금토일])(?:요일)?(?:까지|엔|에\s*마감)",
            cleaned,
        )
        if m_weekday:
            prefix = (m_weekday.group(1) or "").replace(" ", "")
            day_name = m_weekday.group(2)
            target_w = WEEKDAYS_MAP[day_name]
            cur_w = ref_date.weekday()

            if "다다음주" in prefix:
                days_ahead = (7 - cur_w) + 7 + target_w
            elif "다음주" in prefix:
                days_ahead = (7 - cur_w) + target_w
            else:
                # 이번주 또는 명시적 접두사 없음
                days_ahead = target_w - cur_w
                if days_ahead < 0:
                    # 이미 지난 요일이면 다음 주로 간주
                    days_ahead += 7

            target_date = ref_date + timedelta(days=days_ahead)
            norm_text = cleaned[:m_weekday.start()].strip() + " " + cleaned[m_weekday.end():].strip()
            norm_text = norm_text.strip()
            return target_date, f"{norm_text} ~{target_date.strftime('%Y-%m-%d')}".strip()

        # 예: "9월 20일까지", "2026년 9월 20일까지"
        m_korean_date = re.search(
            r"\b(?:(20\d{2})년\s*)?(0?[1-9]|1[0-2])월\s*(0?[1-9]|[12]\d|3[01])일(?:까지|엔|에\s*마감)",
            cleaned,
        )
        if m_korean_date:
            y_str = m_korean_date.group(1)
            y = int(y_str) if y_str else ref_date.year
            m = int(m_korean_date.group(2))
            d = int(m_korean_date.group(3))
            try:
                target_date = date(y, m, d)
                if not y_str and target_date < ref_date and (ref_date - target_date).days > 30:
                    target_date = date(y + 1, m, d)
                norm_text = cleaned[:m_korean_date.start()].strip() + " " + cleaned[m_korean_date.end():].strip()
                norm_text = norm_text.strip()
                return target_date, f"{norm_text} ~{target_date.strftime('%Y-%m-%d')}".strip()
            except ValueError:
                pass

        # 예: "N일 뒤까지", "N일 후까지"
        m_after_days = re.search(r"\b(\d{1,2})\s*일\s*(?:뒤|후)(?:까지|엔|에\s*마감)", cleaned)
        if m_after_days:
            days_count = int(m_after_days.group(1))
            target_date = ref_date + timedelta(days=days_count)
            norm_text = cleaned[:m_after_days.start()].strip() + " " + cleaned[m_after_days.end():].strip()
            norm_text = norm_text.strip()
            return target_date, f"{norm_text} ~{target_date.strftime('%Y-%m-%d')}".strip()

        # 마감일 없음
        return None, cleaned

    @classmethod
    def calculate_dday(
        cls,
        due_date: date,
        base_date: date | datetime | None = None,
    ) -> dict[str, Any]:
        """
        마감일(due_date)과 기준 일자 사이의 D-Day 간격 및 긴급도 상태를 산출합니다.
        - overdue: 기한 초과 (diff < 0)
        - today: 오늘 마감 (diff == 0)
        - urgent: 마감 임박 (1 <= diff <= 3)
        - upcoming: 여유 있는 마감 (diff > 3)
        """
        ref_date = cls._resolve_base_date(base_date)
        diff_days = (due_date - ref_date).days

        if diff_days < 0:
            past_days = abs(diff_days)
            return {
                "due_date": due_date.isoformat(),
                "diff_days": diff_days,
                "status": "overdue",
                "status_code": 0,
                "label": f"⛔ 기한 초과 (D+{past_days})",
                "badge": f"[⛔ Overdue D+{past_days}]",
                "short_badge": f"D+{past_days}",
                "priority_weight": 100 + past_days,
                "desc": f"{past_days}일 지남",
            }
        elif diff_days == 0:
            return {
                "due_date": due_date.isoformat(),
                "diff_days": diff_days,
                "status": "today",
                "status_code": 1,
                "label": "🚨 오늘 마감 (D-Day)",
                "badge": "[🚨 D-Day]",
                "short_badge": "D-Day",
                "priority_weight": 90,
                "desc": "오늘 마감",
            }
        elif 1 <= diff_days <= 3:
            return {
                "due_date": due_date.isoformat(),
                "diff_days": diff_days,
                "status": "urgent",
                "status_code": 2,
                "label": f"⚠️ 마감 임박 (D-{diff_days})",
                "badge": f"[⚠️ D-{diff_days}]",
                "short_badge": f"D-{diff_days}",
                "priority_weight": 80 - diff_days,
                "desc": f"{diff_days}일 남음",
            }
        else:
            return {
                "due_date": due_date.isoformat(),
                "diff_days": diff_days,
                "status": "upcoming",
                "status_code": 3,
                "label": f"📅 D-{diff_days}",
                "badge": f"[📅 D-{diff_days}]",
                "short_badge": f"D-{diff_days}",
                "priority_weight": max(1, 40 - diff_days),
                "desc": f"{diff_days}일 남음",
            }

    @classmethod
    def parse_task_line(
        cls,
        line: str,
        base_date: date | datetime | None = None,
    ) -> dict[str, Any] | None:
        """
        단일 마크다운 태스크 라인('- [ ] ...')에서 마감일과 D-Day 메타데이터를 파싱합니다.
        마감일이 없는 라인이거나 완료된 태스크('- [x]')이면 None을 반환하거나 마감 정보 없는 dict를 반환합니다.
        """
        sline = line.strip()
        if not sline.startswith("- [ ]"):
            return None

        content = sline[5:].strip()
        due_date, _ = cls.extract_due_date_from_text(content, base_date=base_date)
        if not due_date:
            return None

        dday_info = cls.calculate_dday(due_date, base_date=base_date)

        # 디스플레이용 태스크 본문에서 마감 태그는 유지하거나 정리
        clean_display = re.sub(r"~(20\d{2}[-/.])?(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])", "", content).strip()
        clean_display = re.sub(r"@due\([^)]+\)", "", clean_display).strip()
        clean_display = re.sub(r"\((?:마감|기한|due)[^)]+\)", "", clean_display).strip()
        clean_display = re.sub(r"\s+", " ", clean_display)

        return {
            "raw_line": sline,
            "content": content,
            "display_title": clean_display or content,
            "due_date": due_date,
            "due_date_str": due_date.strftime("%Y-%m-%d"),
            **dday_info,
        }

    @classmethod
    def scan_gtd_due_tasks(
        cls,
        base_dir: str,
        base_date: date | datetime | None = None,
    ) -> dict[str, Any]:
        """
        지정된 GTD 작업 디렉토리의 next_actions.md 및 inbox.md(수집함)을 스캔하여
        마감일이 지정된 미완료 태스크들을 추출하고 긴급도별로 분류 및 정렬합니다.
        """
        base_dir = os.path.abspath(os.path.expanduser(base_dir))
        next_actions_path = os.path.join(base_dir, "gtd", "next_actions.md")
        inbox_path = os.path.join(base_dir, "gtd", "inbox.md")
        if not os.path.exists(inbox_path):
            inbox_path = os.path.join(base_dir, "inbox.md")

        files_to_scan = [
            ("next_actions", next_actions_path, "⚡ 다음 행동"),
            ("inbox", inbox_path, "📥 수집함"),
        ]

        all_tasks: list[dict[str, Any]] = []

        for source_id, file_path, source_label in files_to_scan:
            if not os.path.exists(file_path):
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        task_data = cls.parse_task_line(line, base_date=base_date)
                        if task_data:
                            task_data["source_id"] = source_id
                            task_data["source_label"] = source_label
                            all_tasks.append(task_data)
            except OSError as e:
                logger.warning(f"Error scanning due dates in {file_path}: {e}")

        # 정렬: 기한 초과(가장 오래 지난 순) -> 오늘 마감 -> 마감 임박 -> 향후 일정순 (diff_days 오름차순)
        all_tasks.sort(key=lambda t: (t["diff_days"], -t["priority_weight"]))

        overdue_tasks = [t for t in all_tasks if t["status"] == "overdue"]
        today_tasks = [t for t in all_tasks if t["status"] == "today"]
        urgent_tasks = [t for t in all_tasks if t["status"] == "urgent"]
        upcoming_tasks = [t for t in all_tasks if t["status"] == "upcoming"]

        return {
            "total_count": len(all_tasks),
            "overdue_count": len(overdue_tasks),
            "today_count": len(today_tasks),
            "urgent_count": len(urgent_tasks),
            "upcoming_count": len(upcoming_tasks),
            "action_needed_count": len(overdue_tasks) + len(today_tasks) + len(urgent_tasks),
            "overdue_tasks": overdue_tasks,
            "today_tasks": today_tasks,
            "urgent_tasks": urgent_tasks,
            "upcoming_tasks": upcoming_tasks,
            "all_tasks": all_tasks,
        }

    @classmethod
    def format_dday_briefing_section(
        cls,
        base_dir: str,
        base_date: date | datetime | None = None,
    ) -> str:
        """
        아침 브리핑(Morning Briefing) 상단에 삽입할 GTD 마감일 & D-Day 알림 섹션 마크다운을 생성합니다.
        조치 필요한 항목(기한 초과, 오늘 마감, 마감 임박)이 있는 경우 눈에 띄는 경고 블록을 반환하며,
        마감 태스크가 전혀 없거나 여유 있는 경우 간결하게 표시합니다.
        """
        scan_res = cls.scan_gtd_due_tasks(base_dir, base_date=base_date)
        total = scan_res["total_count"]
        action_count = scan_res["action_needed_count"]

        if total == 0:
            return ""

        lines = ["#### ⏳ **GTD 마감일 & D-Day 알림 (Due Date Alerts)**"]

        if action_count == 0:
            # 임박 과제 없음, 향후 마감만 존재
            upcoming = scan_res["upcoming_tasks"][:3]
            lines.append("현재 기한 초과나 마감 임박한 긴급 과제는 없습니다! 평온한 하루 보내세요. ☕")
            for t in upcoming:
                lines.append(f"* 📅 **`{t['display_title']}`** (D-{t['diff_days']}, ~{t['due_date_str']}) - {t['source_label']}")
            return "\n".join(lines)

        # 조치 필요한 긴급 항목이 있는 경우
        if scan_res["overdue_tasks"]:
            lines.append("* ⛔ **기한 초과 (Overdue - 즉시 확인 필요)**:")
            for t in scan_res["overdue_tasks"]:
                lines.append(f"  * ▫️ `{t['display_title']}` (`D+{abs(t['diff_days'])}일 지남`, ~{t['due_date_str']}) - {t['source_label']}")

        if scan_res["today_tasks"]:
            lines.append("* 🚨 **오늘 마감 (D-Day - 오늘 중 완수 필수)**:")
            for t in scan_res["today_tasks"]:
                lines.append(f"  * ▫️ `{t['display_title']}` (`오늘 마감`, ~{t['due_date_str']}) - {t['source_label']}")

        if scan_res["urgent_tasks"]:
            lines.append("* ⚠️ **마감 임박 (D-1 ~ D-3)**:")
            for t in scan_res["urgent_tasks"]:
                lines.append(f"  * ▫️ `{t['display_title']}` (`D-{t['diff_days']}일 남음`, ~{t['due_date_str']}) - {t['source_label']}")

        if scan_res["upcoming_tasks"]:
            up_sample = scan_res["upcoming_tasks"][:2]
            lines.append(f"* 📅 **향후 마감 ({len(scan_res['upcoming_tasks'])}개)**: " + ", ".join([f"`{t['display_title']}` (D-{t['diff_days']})" for t in up_sample]))

        return "\n".join(lines)

    @classmethod
    def format_standalone_deadline_report(
        cls,
        base_dir: str,
        base_date: date | datetime | None = None,
    ) -> str:
        """
        '/dday', '/deadline', '마감일 확인' 질의 시 반환되는 독립 D-Day 마감 리포트 마크다운을 반환합니다.
        """
        ref_date = cls._resolve_base_date(base_date)
        date_label = ref_date.strftime("%Y-%m-%d")
        scan_res = cls.scan_gtd_due_tasks(base_dir, base_date=ref_date)
        total = scan_res["total_count"]

        lines = [
            f"### ⏳ **GTD 마감일(D-Day) 현황 종합 리포트** (`{date_label}` 기준)\n",
        ]

        if total == 0:
            lines.append("현재 GTD 저장소(Next Actions 및 Inbox)에 마감일(`~YYYY-MM-DD`, `@due`)이 설정된 태스크가 없습니다.")
            lines.append("\n💡 **마감일 등록 팁:**")
            lines.append("* 대화창에 `다음 주 수요일까지 자동차 정기검사 예약 gtd에 넣어줘`와 같이 말씀하시거나,")
            lines.append("* 태스크 뒤에 `~2026-09-25` 또는 `~09-25` 태그를 부착하시면 자동으로 D-Day를 추적하고 브리핑해 드립니다! ✨")
            return "\n".join(lines)

        overdue_cnt = scan_res["overdue_count"]
        today_cnt = scan_res["today_count"]
        urgent_cnt = scan_res["urgent_count"]
        upcoming_cnt = scan_res["upcoming_count"]

        summary_badges = []
        if overdue_cnt:
            summary_badges.append(f"⛔ 기한초과: **{overdue_cnt}개**")
        if today_cnt:
            summary_badges.append(f"🚨 오늘마감: **{today_cnt}개**")
        if urgent_cnt:
            summary_badges.append(f"⚠️ 임박(3일이내): **{urgent_cnt}개**")
        if upcoming_cnt:
            summary_badges.append(f"📅 예정: **{upcoming_cnt}개**")

        lines.append(f"• **마감 일정 요약**: {' | '.join(summary_badges)} (총 {total}개)\n")

        # 섹션별 상세 목록
        if scan_res["overdue_tasks"]:
            lines.append("#### ⛔ **1. 기한 초과 (Overdue)**")
            for t in scan_res["overdue_tasks"]:
                lines.append(f"* **`{t['display_title']}`**")
                lines.append(f"  * 기한: `{t['due_date_str']}` (**{abs(t['diff_days'])}일 지남**) | 위치: {t['source_label']}")
            lines.append("")

        if scan_res["today_tasks"]:
            lines.append("#### 🚨 **2. 오늘 마감 (D-Day)**")
            for t in scan_res["today_tasks"]:
                lines.append(f"* **`{t['display_title']}`**")
                lines.append(f"  * 기한: `{t['due_date_str']}` (**오늘 마감 🎯**) | 위치: {t['source_label']}")
            lines.append("")

        if scan_res["urgent_tasks"]:
            lines.append("#### ⚠️ **3. 마감 임박 (D-1 ~ D-3)**")
            for t in scan_res["urgent_tasks"]:
                lines.append(f"* **`{t['display_title']}`**")
                lines.append(f"  * 기한: `{t['due_date_str']}` (**{t['diff_days']}일 남음**) | 위치: {t['source_label']}")
            lines.append("")

        if scan_res["upcoming_tasks"]:
            lines.append("#### 📅 **4. 향후 마감 과제 (Upcoming)**")
            for t in scan_res["upcoming_tasks"]:
                lines.append(f"* **`{t['display_title']}`**")
                lines.append(f"  * 기한: `{t['due_date_str']}` (**D-{t['diff_days']}**) | 위치: {t['source_label']}")
            lines.append("")

        lines.append("💡 완료하신 작업은 `/done [과제명]` 또는 브리핑 인라인 버튼으로 완료 처리하시면 자동으로 일일 로그로 수술적 이관(Cut & Paste)됩니다!")
        return "\n".join(lines)

    @classmethod
    def prioritize_next_actions(
        cls,
        next_actions: list[str],
        base_date: date | datetime | None = None,
    ) -> list[str]:
        """
        Next Actions 목록을 D-Day 긴급도 가중치(기한초과 > 오늘마감 > 임박 > 기타)를 반영하여 재정렬합니다.
        """
        ref_date = cls._resolve_base_date(base_date)

        scored: list[tuple[int, int, str]] = []
        for idx, act in enumerate(next_actions):
            task_data = cls.parse_task_line(f"- [ ] {act}", base_date=ref_date)
            if task_data:
                # priority_weight는 기한초과(100+), 오늘(90), 임박(77~79), 기타(1~40)
                weight = task_data["priority_weight"]
            else:
                # 마감 태그가 없더라도 긴급 키워드가 있다면 기본 가중치 부여
                if any(k in act for k in ["🚨", "오늘", "마감", "긴급", "중요", "P1"]):
                    weight = 60
                else:
                    weight = 0
            # weight 내림차순, 동일 가중치일 경우 원래 인덱스 순서 유지
            scored.append((weight, idx, act))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored]

    @staticmethod
    def _resolve_base_date(base_date: date | datetime | None) -> date:
        if base_date is None:
            return get_now().date()
        if isinstance(base_date, datetime):
            return base_date.date()
        return base_date
