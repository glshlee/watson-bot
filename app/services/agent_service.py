import logging
import os
import re
from datetime import datetime

from app.config import get_app_timezone, get_now

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

        content_lower = content.lower()
        target_idx = -1

        # 1. 문맥 맞춤형 섹션 우선 탐색 (ADR-014)
        # (1-1) 개인 생활 / 건강 / 여행 / 맛집 / 구매
        if any(k in content_lower for k in ["여행", "맛집", "어죽", "게국지", "와이프", "가족", "개인", "생활", "건강", "병원", "초음파", "구매", "장보기", "휴지", "원두", "모래", "독서", "은퇴", "교육", "personal"]):
            for i, line in enumerate(lines):
                if re.search(r"^##\s*.*?(개인|생활|건강|personal)", line, re.IGNORECASE):
                    target_idx = i
                    break

        # (1-2) 회사 업무 / 프로젝트 / 회의
        if target_idx == -1 and any(k in content_lower for k in ["회사", "업무", "회의", "보고", "아젠다", "가이드라인", "배포", "기획", "개발", "work"]):
            for i, line in enumerate(lines):
                if re.search(r"^##\s*.*?(회사|업무|work)", line, re.IGNORECASE):
                    target_idx = i
                    break

        # (1-3) 인프라 및 시스템
        if target_idx == -1 and any(k in content_lower for k in ["인프라", "토큰", "oauth", "서버", "infra"]):
            for i, line in enumerate(lines):
                if re.search(r"^##\s*.*?(인프라|infra|시스템)", line, re.IGNORECASE):
                    target_idx = i
                    break

        # (1-4) 사이드 프로젝트
        if target_idx == -1 and any(k in content_lower for k in ["사이드", "브이로그", "숏폼", "펭귄", "캐릭터", "side"]):
            for i, line in enumerate(lines):
                if re.search(r"^##\s*.*?(사이드|side)", line, re.IGNORECASE):
                    target_idx = i
                    break

        # 2. 일반 빠른 메모 / Inbox 섹션 폴백
        if target_idx == -1:
            target_headers = [
                "## 💬 빠른 메모 / 캡처",
                "## 📥 GTD Inbox",
                "## 빠른 메모",
                "## Inbox",
                "## 수집함",
            ]
            for i, line in enumerate(lines):
                for th in target_headers:
                    if th.lower() in line.lower():
                        target_idx = i
                        break
                if target_idx != -1:
                    break

        # 태스크 포맷팅 정제
        task_item = content.strip()
        if not task_item.startswith("- ["):
            task_item = f"- [ ] {task_item}"

        # 캡처 뱃지 부여 (순수 텍스트 캡처 시 *(Watson 캡처)* 부여, 이미 이모지/포맷팅 포함 시 유지)
        if not any(marker in task_item for marker in ["*(Watson 캡처)*", "🚗", "🍲", "✈️", "🛒", "💊", "🏥", "🏢", "💻", "🚨"]):
            task_item = f"{task_item} *(Watson 캡처)*"

        task_item = f"{task_item.strip()}\n"

        if target_idx != -1:
            lines.insert(target_idx + 1, task_item)
        else:
            lines.append(f"\n## 💬 빠른 메모 / 캡처 (Watson & Quick Capture)\n{task_item}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

        logger.info(f"Appended task to GTD inbox: {filepath}")
        return filepath


    def _normalize_datetime(self, date_obj: datetime | None = None) -> datetime:
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

    def get_lifelog_filepath(self, date_obj: datetime | None = None) -> str:
        date_obj = self._normalize_datetime(date_obj)
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
        date_obj = self._normalize_datetime(date_obj)

        # Check if this category represents a GTD Inbox task and repository has GTD structure
        gtd_task_categories = ["GTD Inbox", "GTD", "Task", "Todo", "Quick Capture", "할일"]
        if any(cat.lower() in category.lower() for cat in gtd_task_categories) and self.has_gtd_inbox():
            return self.append_to_gtd_inbox(content)

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

    def get_gtd_summary(self, date_obj: datetime | None = None) -> str:
        """
        연결된 GTD 저장소에서 오늘의 일정, Next Actions, Inbox 항목을 종합 추출하여
        비서 브리핑 메시지를 생성합니다 (ADR-008, ADR-013).
        """
        date_obj = self._normalize_datetime(date_obj)
        date_str = date_obj.strftime("%Y-%m-%d")

        schedule_items: list[str] = []
        next_actions: list[str] = []
        inbox_items: list[str] = []

        # 1. 데일리 로그의 오늘 일정 (Schedule) 추출
        daily_path = self.get_lifelog_filepath(date_obj)
        if not os.path.exists(daily_path) and self.has_daily_logs_structure():
            daily_dir = os.path.join(self.base_dir, "logs", "daily")
            files = sorted([f for f in os.listdir(daily_dir) if f.endswith(".md")], reverse=True)
            if files:
                daily_path = os.path.join(daily_dir, files[0])

        if os.path.exists(daily_path):
            try:
                with open(daily_path, "r", encoding="utf-8") as f:
                    in_schedule = False
                    for line in f:
                        line_s = line.strip()
                        if "주요 일정" in line_s or "Schedule" in line_s:
                            in_schedule = True
                            continue
                        if in_schedule and line_s.startswith("## "):
                            in_schedule = False
                        if in_schedule and line_s.startswith(("- [", "- ")):
                            item = re.sub(r"^-\s*(\[[ xX]\]\s*)?", "", line_s).strip()
                            if item and not item.startswith("("):
                                schedule_items.append(item)
            except OSError as e:
                logger.warning(f"Failed to read daily log: {e}")

        # 2. Next Actions (다음 행동) 추출
        next_actions_path = os.path.join(self.base_dir, "gtd", "next_actions.md")
        if os.path.exists(next_actions_path):
            try:
                with open(next_actions_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line_s = line.strip()
                        if line_s.startswith("- [ ]"):
                            item = line_s[5:].strip()
                            if item:
                                next_actions.append(item)
            except OSError as e:
                logger.warning(f"Failed to read next_actions.md: {e}")

        # 3. GTD Inbox (수집함 미처리 항목) 추출
        inbox_path = self.get_gtd_inbox_filepath()
        if os.path.exists(inbox_path):
            try:
                with open(inbox_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line_s = line.strip()
                        if line_s.startswith("- [ ]"):
                            item = line_s[5:].strip()
                            if item and not item.startswith("("):
                                inbox_items.append(item)
            except OSError as e:
                logger.warning(f"Failed to read inbox.md: {e}")

        # 포맷팅 브리핑 메시지 구성
        sections = [f"📋 **오늘의 일정 및 GTD 할 일 브리핑 ({date_str})** ☀️\n"]

        if schedule_items:
            sections.append("📅 **오늘의 주요 일정:**")
            for item in schedule_items[:5]:
                sections.append(f"• {item}")
            sections.append("")

        if next_actions:
            sections.append("⚡ **실행 대기 주요 작업 (Next Actions):**")
            urgent = [a for a in next_actions if "🚨" in a or "오늘" in a or "마감" in a]
            normal = [a for a in next_actions if a not in urgent]
            ordered = urgent + normal
            for item in ordered[:6]:
                sections.append(f"• {item}")
            sections.append("")

        if inbox_items:
            sections.append("📥 **수집함 미처리 메모 (Inbox):**")
            for item in inbox_items[:3]:
                sections.append(f"• {item}")
            sections.append("")

        if not schedule_items and not next_actions and not inbox_items:
            sections.append("현재 등록된 미완료 할 일이나 일정이 없습니다. 가벼운 마음으로 오늘 하루를 시작해 보세요! ☕")
        else:
            sections.append("오늘도 보람찬 하루 되실 수 있도록 왓슨이 든든히 서포트하겠습니다! 무엇부터 함께 해볼까요? 💪✨")

        return "\n".join(sections)

    def remove_gtd_tasks(self, keywords: list[str]) -> list[str]:
        """
        gtd/inbox.md 및 gtd/next_actions.md에서 주어진 키워드들을 포함하는 태스크 라인을 제거합니다.
        제거된 태스크 명칭 목록을 반환합니다.
        """
        removed_tasks: list[str] = []
        if not keywords:
            return removed_tasks

        gtd_files = [
            self.get_gtd_inbox_filepath(),
            os.path.join(self.base_dir, "gtd", "next_actions.md"),
        ]

        # 2글자 이상의 의미 있는 키워드 정규화
        clean_keywords = [
            k.strip().lower()
            for k in keywords
            if len(k.strip()) >= 2 and k.strip().lower() not in ["제거", "삭제", "완료", "할일", "작업", "태스크"]
        ]

        if not clean_keywords:
            return removed_tasks

        for filepath in gtd_files:
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except OSError as e:
                logger.warning(f"Failed to read {filepath}: {e}")
                continue

            new_lines = []
            file_modified = False

            for line in lines:
                line_s = line.strip()
                if line_s.startswith(("- [ ]", "- [x]")):
                    line_lower = line_s.lower()
                    matched = False
                    for kw in clean_keywords:
                        # 공백 제거 비교도 함께 지원 (예: '주간 보고' vs '주간보고')
                        kw_nospace = kw.replace(" ", "")
                        line_nospace = line_lower.replace(" ", "")
                        if kw in line_lower or kw_nospace in line_nospace:
                            matched = True
                            task_name = re.sub(r"^-\s*\[[ x]\]\s*", "", line_s)
                            task_name = re.sub(r"[\*`]", "", task_name).strip()

                            if task_name and task_name not in removed_tasks:
                                removed_tasks.append(task_name)
                            file_modified = True
                            break
                    if not matched:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            if file_modified:
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    logger.info(f"Removed tasks from {filepath}: {removed_tasks}")
                except OSError as e:
                    logger.error(f"Failed to write to {filepath}: {e}")

        return removed_tasks

    def find_and_remove_matching_tasks(self, user_message: str) -> list[str]:
        """
        사용자 메시지에서 삭제/제거 의도를 감지하여, 기존 GTD 저장소(inbox.md, next_actions.md)의
        실제 등록된 태스크 목록과 대조하여 일치하는 태스크를 안전하게 제거합니다.
        """
        gtd_files = [
            self.get_gtd_inbox_filepath(),
            os.path.join(self.base_dir, "gtd", "next_actions.md"),
        ]
        active_tasks: list[str] = []
        for filepath in gtd_files:
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            line_s = line.strip()
                            if line_s.startswith("- [ ]"):
                                item = line_s[5:].strip()
                                item_clean = re.sub(r"[\*`]", "", item).strip()

                                if item_clean and item_clean not in active_tasks:
                                    active_tasks.append(item_clean)
                except OSError:
                    pass

        user_msg_lower = user_message.lower()
        matched_keywords: list[str] = []

        # (A) 구문별 분리 ("tiara_ad는 제거해", "주간보고 제거", ...)
        clauses = re.split(r"[,.\n및]+", user_message)
        for clause in clauses:
            clause_clean = clause.strip()
            if any(term in clause_clean for term in ["제거", "삭제", "빼", "지워", "제외", "완료", "해결"]):
                kw = re.sub(r"(?:는|도|은|를|을|에\s*대해)?\s*(?:제거해|제거|삭제해|삭제|빼줘|빼|지워줘|지워|제외해|제외|완료해|완료).*$", "", clause_clean).strip()
                if len(kw) >= 2:
                    matched_keywords.append(kw)

        # (B) 활성 태스크와의 직접 대조 (오타 '나내' -> '아내' 등 부분 일치 보정)
        for task in active_tasks:
            words = [w for w in re.split(r"[\s\(\)\[\]\-]+", task) if len(w) >= 2]
            for w in words:
                w_lower = w.lower()
                if len(w) >= 3 and (w_lower in user_msg_lower or (w in ["건강회복", "임신케어", "주간보고"] and any(part in user_msg_lower for part in [w, w.replace(" ", "")]))):
                    matched_keywords.append(w)
            # 가족을 위한 시간 보내기 등의 구문
            if "가족" in task and "가족" in user_msg_lower and any(t in user_msg_lower for t in ["제거", "삭제", "빼"]):
                matched_keywords.append("가족")
            if "건강" in task and ("건강" in user_msg_lower or "회복" in user_msg_lower) and any(t in user_msg_lower for t in ["제거", "삭제", "빼"]):
                matched_keywords.append("건강")

        matched_keywords = list(set(matched_keywords))
        return self.remove_gtd_tasks(matched_keywords)

