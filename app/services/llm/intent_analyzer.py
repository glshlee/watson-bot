from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass

from app.config import settings
from app.services.llm.category_extractor import detect_category


@dataclass
class IntentResult:
    """
    슬래시(/) 명령어 라우팅 및 LLM 응답 전달을 위한 결과 컨테이너 (ADR-066).
    - 자연어 입력에 대해서는 파이썬이 인텐트를 분류하지 않고 무조건 `intent="chat_only"`로 LLM 응답만 전달합니다.
    - 오직 명시적인 `/` 슬래시 명령어 또는 보류된 초안(pending_log) 승인/거절 시에만 해당 워크플로우 키를 반환합니다.
    """

    intent: str
    ai_response: str
    log_content: str | None = None
    category: str | None = None
    gtd_task_content: str | None = None
    is_dual_log: bool = False


def _handle_slash_command(prompt_clean: str) -> IntentResult:
    """
    명시적인 슬래시(/) 명령어에 대해 결정론적 고속 실행을 위한 워크플로우 키를 반환합니다 (ADR-061, ADR-066).
    """
    prompt_lower = prompt_clean.lower()
    cmd = prompt_lower.split()[0]

    # 1. 일일 로그 및 GTD 파일 직접 조회
    if cmd in ["/today", "/daily"]:
        return IntentResult(intent="daily_log_inspect", ai_response="", category="LifeLog")
    if cmd in ["/gtd", "/inbox"]:
        return IntentResult(intent="gtd_inspect", ai_response="", category="GTD")
    if cmd in ["/gtd-today", "/today-gtd", "/all-log"]:
        return IntentResult(intent="gtd_and_log_inspect", ai_response="", category="GTD")
    if cmd in ["/dday", "/deadline"]:
        return IntentResult(intent="dday_inspect", ai_response="", category="GTD")

    # 2. 브리핑 및 스케줄
    if cmd == "/schedule":
        return IntentResult(intent="briefing_schedule_inspect", ai_response="", category="GTD")
    if prompt_lower.startswith("/briefing"):
        sub = prompt_lower[9:].strip()
        if sub in ["morning", "am", "아침"]:
            return IntentResult(intent="task_briefing_morning", ai_response="", category="GTD")
        if sub in ["evening", "pm", "저녁", "회고"]:
            return IntentResult(intent="task_briefing_evening", ai_response="", category="GTD")
        if sub in ["schedule", "스케줄", "스케쥴"]:
            return IntentResult(intent="briefing_schedule_inspect", ai_response="", category="GTD")
        return IntentResult(intent="task_briefing", ai_response="", category="GTD")

    # 3. 명시적 라이프로그 기록 패스트트랙 (/log)
    if prompt_clean.startswith("/log"):
        log_body = prompt_clean[4:].strip()
        cat = detect_category(log_body) if log_body else "Daily Notes & Diary"
        return IntentResult(
            intent="log_explicit",
            ai_response=f"명령해 주신 내용을 오늘 자 라이프로그 **[{cat}]**에 즉시 기록했습니다! 📄✨",
            log_content=log_body,
            category=cat,
        )

    # 4. GTD 태스크 완료 패스트트랙 (/done)
    if prompt_lower.startswith("/done"):
        target_task = prompt_clean[5:].strip()
        return IntentResult(intent="task_complete", ai_response="", log_content=target_task, category="GTD")

    # 5. Git 원격 동기화, 커밋, 푸시
    if cmd == "/sync":
        return IntentResult(intent="repo_sync", ai_response="", category="GTD")
    if cmd == "/commit":
        return IntentResult(intent="repo_commit", ai_response="", category="Git")
    if cmd == "/push":
        return IntentResult(intent="repo_push", ai_response="", log_content="push", category="Git")

    # 6. 검색 및 주간 결산
    if cmd in ["/search", "/find"]:
        parts = prompt_clean.split(maxsplit=1)
        search_kw = parts[1].strip() if len(parts) > 1 else ""
        return IntentResult(intent="search_query", ai_response="", log_content=search_kw, category="Search")
    if cmd in ["/weekly", "/review"]:
        return IntentResult(intent="weekly_review", ai_response="", category="WeeklyReview")

    # 7. 비전 분석
    if cmd in ["/vision", "/photo"]:
        parts = prompt_clean.split(maxsplit=2)
        target_path = parts[1].strip() if len(parts) > 1 else ""
        caption = parts[2].strip() if len(parts) > 2 else ""
        return IntentResult(
            intent="vision_inspect",
            ai_response="",
            log_content=json.dumps({"path": target_path, "caption": caption}, ensure_ascii=False),
            category="Vision",
        )

    # 8. 인플레이스 에디터 및 잔디
    if cmd in ["/edit", "/editor"]:
        parts = prompt_clean.split(maxsplit=1)
        target_date = parts[1].strip() if len(parts) > 1 else ""
        return IntentResult(intent="lifelog_edit", ai_response="", log_content=target_date, category="LifeLogEditor")
    if cmd in ["/heatmap", "/잔디"]:
        return IntentResult(intent="lifelog_heatmap", ai_response="", category="Heatmap")

    # 9. 동네 및 출근길
    if cmd in ["/location", "/동네"]:
        parts = prompt_clean.split(maxsplit=1)
        loc_query = parts[1].strip() if len(parts) > 1 else ""
        return IntentResult(
            intent="location_set" if loc_query else "location_inspect",
            ai_response="",
            log_content=loc_query if loc_query else None,
            category="Commute",
        )
    if cmd in ["/commute", "/bus", "/weather", "/air"]:
        if any(k in prompt_lower for k in ["test", "preview", "미리보기", "테스트"]):
            sub_mode = "preview"
        elif cmd in ["/bus", "/버스"]:
            sub_mode = "bus"
        elif cmd in ["/weather", "/air"]:
            sub_mode = "weather"
        else:
            sub_mode = "status"
        return IntentResult(intent="commute_inspect", ai_response="", log_content=sub_mode, category="Commute")

    # 10. 웹 대시보드 URL
    if cmd in ["/url", "/web", "/link", "/tunnel"]:
        url_file = os.path.join(settings.REPO_PATH, "tunnel_url.txt")
        current_url = ""
        if os.path.exists(url_file):
            try:
                with open(url_file, "r", encoding="utf-8") as f:
                    current_url = f.read().strip()
            except OSError:
                pass
        if current_url:
            resp = (
                "🌐 **Watson 웹 대시보드 접속 주소**\n\n"
                f"🔗 {current_url}\n\n"
                "• 🏠 **에이전트 허브 포털**: `/`\n"
                "• 🤖 **왓슨 비서 콘솔**: `/watson`\n"
                "• 💻 **개발 에이전트 DevBot**: `/dev`\n"
            )
        else:
            resp = "🌐 현재 외부 Cloudflare Tunnel 주소를 확인할 수 없습니다. 로컬 환경(`http://localhost:8000`)을 확인해 주세요."
        return IntentResult(intent="web_url_query", ai_response=resp, category="System")

    # 11. 상태 확인
    if cmd == "/status":
        return IntentResult(intent="log_status_inspect", ai_response="", category="LifeLog")

    return IntentResult(
        intent="chat_only",
        ai_response=f"알 수 없는 슬래시 명령어('{prompt_clean}')입니다. 사용 가능한 명령어를 확인하시려면 [/] 팔레트를 열어보세요.",
    )


def analyze_intent(
    prompt: str,
    history: list[dict[str, str]] | None = None,
    pending_log: dict[str, str] | None = None,
    gtd_path: str | None = None,
    call_ai_engine_func: Callable[[str, list[dict[str, str]] | None], str] | None = None,
) -> IntentResult:
    """
    파이썬 측 자연어 인텐트 분류기를 전면 제거한 순수 라우터 (ADR-066).
    1) Vision 사진 등 보류된 초안(pending_log)에 대한 짧은 승인/거절 토큰 처리
    2) 명시적 슬래시(/) 명령어 결정론적 패스트트랙 처리
    3) 그 외 모든 자연어는 인텐트 분류 없이 100% LLM(AGY 에이전트)에 전달하고 응답을 그대로 반환
    """
    prompt_clean = prompt.strip()

    # 1. 보류 중인 초안(Vision 사진 분석 카드 등)에 대한 단순 승인/거절 처리
    if pending_log:
        if re.search(r"^(아니|아니야|아냐|취소|괜찮아|아니\s*괜찮아|no|cancel)[\.\!\?\s]*$", prompt_clean, re.IGNORECASE):
            return IntentResult(
                intent="log_reject",
                ai_response="네, 기록하지 않고 취소했습니다! 😊",
            )
        if re.search(
            r"^(응|어|네|예|그래|좋아|좋아요|ㅇㅇ|yes|ok|이대로|응\s*좋아|응\s*좋아\s*기록해줘|응\s*기록해줘|기록해줘)[\.\!\?\s]*$",
            prompt_clean,
            re.IGNORECASE,
        ):
            content = pending_log.get("content", prompt_clean)
            cat = pending_log.get("category", "Daily Notes & Diary")
            gtd_task = pending_log.get("gtd_task")
            is_dual = bool(pending_log.get("is_dual", False) or gtd_task)
            if is_dual and gtd_task:
                return IntentResult(
                    intent="log_dual",
                    ai_response=f"검토해 주신 내용을 오늘 자 **[{cat}]** 및 **GTD 수집함**에 반영했습니다! 📝📥✨",
                    log_content=content,
                    category=cat,
                    gtd_task_content=gtd_task,
                    is_dual_log=True,
                )
            return IntentResult(
                intent="log_confirm",
                ai_response=f"오늘 자 라이프로그 **[{cat}]** 섹션에 기록했습니다! 📝✨",
                log_content=content,
                category=cat,
            )

    # 2. 명시적인 슬래시(/) 명령어 처리
    if prompt_clean.startswith("/"):
        return _handle_slash_command(prompt_clean)

    # 3. 모든 자연어 입력: 파이썬 인텐트 분류 없이 100% LLM(AGY 자율 에이전트) 직접 실행 후 응답 반환
    llm_response = call_ai_engine_func(prompt_clean, history) if call_ai_engine_func else ""
    if not llm_response or not llm_response.strip():
        llm_response = "네, 말씀 잘 들었습니다! 😊 오늘 있었던 일이나 정리할 GTD 할 일이 있다면 편하게 말씀해 주세요."

    return IntentResult(
        intent="chat_only",
        ai_response=llm_response.strip(),
    )
