from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass

from app.config import settings
from app.services.llm.category_extractor import (
    detect_category,
    extract_actionable_task,
)


@dataclass
class IntentResult:
    """비서 에이전트의 의도 분석 및 응답 결과 데이터클래스."""

    intent: str  # "chat_only", "log_suggest", "log_confirm", "log_reject", "log_explicit", "log_dual", "task_briefing", etc.
    ai_response: str
    log_content: str | None = None
    category: str | None = None
    gtd_task_content: str | None = None  # GTD inbox에 등록할 액션 태스크 (ADR-014)
    is_dual_log: bool = False  # 데일리 로그 + GTD 인박스 동시 기록 여부


def _handle_slash_command(prompt_clean: str) -> IntentResult:
    """
    명시적인 슬래시(/) 명령어에 대해 결정론적 즉각 라우팅을 집행합니다 (ADR-061).
    자연어는 절대로 가로채지 않으며, 오직 '/'로 시작하는 표준 명령어만 처리합니다.
    """
    prompt_lower = prompt_clean.lower()
    cmd = prompt_lower.split()[0]

    # 1. 일일 로그 및 GTD 파일 직접 조회
    if cmd in ["/today", "/daily"]:
        return IntentResult(
            intent="daily_log_inspect",
            ai_response="",
            log_content=None,
            category="LifeLog",
        )
    if cmd in ["/gtd", "/inbox"]:
        return IntentResult(
            intent="gtd_inspect",
            ai_response="",
            log_content=None,
            category="GTD",
        )
    if cmd in ["/gtd-today", "/today-gtd", "/all-log"]:
        return IntentResult(
            intent="gtd_and_log_inspect",
            ai_response="",
            log_content=None,
            category="GTD",
        )
    if cmd in ["/dday", "/deadline"]:
        return IntentResult(
            intent="dday_inspect",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    # 2. 브리핑 및 스케줄
    if cmd == "/schedule":
        return IntentResult(
            intent="briefing_schedule_inspect",
            ai_response="",
            log_content=None,
            category="GTD",
        )
    if prompt_lower.startswith("/briefing"):
        sub = prompt_lower[9:].strip()
        if sub in ["morning", "am", "아침"]:
            return IntentResult(
                intent="task_briefing_morning",
                ai_response="",
                log_content=None,
                category="GTD",
            )
        if sub in ["evening", "pm", "저녁", "회고"]:
            return IntentResult(
                intent="task_briefing_evening",
                ai_response="",
                log_content=None,
                category="GTD",
            )
        if sub in ["schedule", "스케줄", "스케쥴"]:
            return IntentResult(
                intent="briefing_schedule_inspect",
                ai_response="",
                log_content=None,
                category="GTD",
            )
        return IntentResult(
            intent="task_briefing",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    # 3. 명시적 라이프로그 기록 패스트트랙
    if prompt_clean.startswith("/log"):
        log_body = prompt_clean[4:].strip()
        cat = detect_category(log_body) if log_body else "Daily Notes & Diary"
        return IntentResult(
            intent="log_explicit",
            ai_response=f"명령해 주신 내용을 오늘 자 라이프로그 **[{cat}]**에 즉시 기록하고 GitHub에 커밋했습니다! 📄🚀",
            log_content=log_body,
            category=cat,
        )

    # 4. GTD 1순위 완료 / 특정 태스크 완료
    if prompt_lower.startswith("/done"):
        target_task = prompt_clean[5:].strip()
        return IntentResult(
            intent="task_complete",
            ai_response="",
            log_content=target_task,
            category="GTD",
        )

    # 5. Git 원격 동기화, 커밋, 푸시
    if cmd == "/sync":
        return IntentResult(
            intent="repo_sync",
            ai_response="",
            log_content=None,
            category="GTD",
        )
    if cmd == "/commit":
        return IntentResult(
            intent="repo_commit",
            ai_response="",
            log_content=None,
            category="Git",
        )
    if cmd == "/push":
        return IntentResult(
            intent="repo_push",
            ai_response="",
            log_content="push",
            category="Git",
        )

    # 6. 검색 및 주간 결산
    if cmd in ["/search", "/find"]:
        parts = prompt_clean.split(maxsplit=1)
        search_kw = parts[1].strip() if len(parts) > 1 else ""
        return IntentResult(
            intent="search_query",
            ai_response="",
            log_content=search_kw,
            category="Search",
        )
    if cmd in ["/weekly", "/review"]:
        return IntentResult(
            intent="weekly_review",
            ai_response="",
            log_content=None,
            category="WeeklyReview",
        )

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
        return IntentResult(
            intent="lifelog_edit",
            ai_response="",
            log_content=target_date,
            category="LifeLogEditor",
        )
    if cmd in ["/heatmap", "/잔디"]:
        return IntentResult(
            intent="lifelog_heatmap",
            ai_response="",
            log_content=None,
            category="Heatmap",
        )

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
        return IntentResult(
            intent="commute_inspect",
            ai_response="",
            log_content=sub_mode,
            category="Commute",
        )

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
                "• 💻 **개발 에이전트 DevBot**: `/dev`\n\n"
                "💡 브라우저 로그인 창(HTTP Basic)에서 설정된 ID/PW로 접속해 주세요."
            )
        else:
            resp = (
                "🌐 현재 외부 Cloudflare Tunnel 주소를 확인할 수 없습니다.\n"
                "로컬 환경(`http://localhost:8000`)에 직접 접속하시거나 터널 상태를 확인해 주세요."
            )
        return IntentResult(
            intent="web_url_query",
            ai_response=resp,
            log_content=None,
            category="System",
        )

    # 11. 상태 확인
    if cmd == "/status":
        return IntentResult(
            intent="log_status_inspect",
            ai_response="",
            log_content=None,
            category="LifeLog",
        )

    # 미등록 슬래시 명령어
    return IntentResult(
        intent="chat_only",
        ai_response=f"알 수 없는 슬래시 명령어('{prompt_clean}')입니다. 사용 가능한 명령어를 확인하시려면 [/] 팔레트를 열어보세요.",
    )


def _parse_llm_intent_result(
    llm_raw: str,
    prompt_clean: str,
    history: list[dict[str, str]] | None = None,
) -> IntentResult:
    """
    LLM의 원문 응답에서 ADR-061 의도 태그([INTENT: ...])를 파싱하고
    비즈니스 액션과 순수 대화 응답 텍스트를 분리 조립합니다.
    """
    if not llm_raw or not llm_raw.strip():
        return IntentResult(
            intent="chat_only",
            ai_response="네, 사용자님 말씀 잘 듣고 있습니다! 😊 오늘 하루 있었던 일과나 나누고 싶은 생각, 혹은 정리할 일정이 있다면 무엇이든 편하게 말씀해 주세요.",
        )

    m = re.search(r"\[INTENT:\s*([a-zA-Z0-9_]+)(.*?)\]", llm_raw, re.DOTALL)
    if not m:
        return IntentResult(intent="chat_only", ai_response=llm_raw.strip())

    intent_tag = m.group(1).strip()
    attr_str = m.group(2).strip()
    attrs: dict[str, str] = {}
    for match in re.finditer(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s\]]+))', attr_str):
        k = match.group(1)
        v = match.group(2) or match.group(3) or match.group(4) or ""
        attrs[k] = v

    ai_response = re.sub(r"\[INTENT:.*?\]\s*", "", llm_raw).strip()

    if intent_tag == "log_suggest":
        cat = attrs.get("category") or detect_category(prompt_clean)
        gtd_task = attrs.get("gtd_task")
        is_dual = bool(gtd_task) or (attrs.get("is_dual") == "true")
        content = attrs.get("content") or prompt_clean
        return IntentResult(
            intent="log_suggest",
            ai_response=ai_response,
            log_content=content,
            category=cat,
            gtd_task_content=gtd_task,
            is_dual_log=is_dual,
        )

    if intent_tag in ["log_explicit", "log_confirm"]:
        cat = attrs.get("category") or detect_category(prompt_clean)
        gtd_task = attrs.get("gtd_task")
        content_opt: str | None = attrs.get("content") or attrs.get("log_content")
        if not content_opt:
            if gtd_task and cat == "GTD Inbox":
                content_opt = f"- [ ] {gtd_task}"
            elif history and any(k in prompt_clean for k in ["아까", "방금", "이전", "앞서", "말한", "위", "내용"]):
                for h in reversed(history):
                    if h.get("role") == "user" and len(h.get("content", "").strip()) > 5:
                        content_opt = h.get("content", "").strip()
                        break
            if not content_opt:
                content_opt = prompt_clean
        elif gtd_task and cat == "GTD Inbox" and not content_opt.startswith("- ["):
            content_opt = f"- [ ] {gtd_task}"
        return IntentResult(
            intent=intent_tag,
            ai_response=ai_response,
            log_content=content_opt,
            category=cat,
            gtd_task_content=gtd_task,
        )

    if intent_tag == "log_dual":
        cat = attrs.get("category", "Daily Notes & Diary")
        content = attrs.get("content") or attrs.get("log_content") or prompt_clean
        gtd_task = attrs.get("gtd_task") or extract_actionable_task(content)
        return IntentResult(
            intent="log_dual",
            ai_response=ai_response,
            log_content=content,
            category=cat,
            gtd_task_content=gtd_task,
            is_dual_log=True,
        )

    if intent_tag == "task_complete":
        target = attrs.get("target") or attrs.get("query") or ""
        return IntentResult(
            intent="task_complete",
            ai_response=ai_response,
            log_content=target,
            category="GTD",
        )

    if intent_tag == "gtd_remove":
        target = attrs.get("target") or prompt_clean
        return IntentResult(
            intent="gtd_remove",
            ai_response=ai_response,
            log_content=target,
            category="GTD",
        )

    if intent_tag == "repo_push":
        mode = attrs.get("mode") or ("query" if any(q in prompt_clean for q in ["어디", "주소", "확인", "맞아"]) else "push")
        return IntentResult(
            intent="repo_push",
            ai_response=ai_response,
            log_content=mode,
            category="Git",
        )

    if intent_tag in ["repo_sync", "repo_sync_and_briefing"]:
        return IntentResult(
            intent=intent_tag,
            ai_response=ai_response,
            log_content=None,
            category="GTD",
        )

    if intent_tag == "repo_commit":
        return IntentResult(
            intent="repo_commit",
            ai_response=ai_response,
            log_content=None,
            category="Git",
        )

    if intent_tag in ["task_briefing_morning", "task_briefing_evening", "task_briefing", "briefing_schedule_inspect"]:
        return IntentResult(
            intent=intent_tag,
            ai_response=ai_response,
            log_content=None,
            category="GTD",
        )

    if intent_tag in ["daily_log_inspect", "gtd_inspect", "gtd_and_log_inspect", "dday_inspect", "log_status_inspect"]:
        return IntentResult(
            intent=intent_tag,
            ai_response=ai_response,
            log_content=None,
            category="GTD" if "gtd" in intent_tag or "dday" in intent_tag else "LifeLog",
        )

    if intent_tag == "commute_inspect":
        mode = attrs.get("mode", "status")
        return IntentResult(
            intent="commute_inspect",
            ai_response=ai_response,
            log_content=mode,
            category="Commute",
        )

    if intent_tag in ["location_set", "location_inspect"]:
        query = attrs.get("query")
        return IntentResult(
            intent=intent_tag,
            ai_response=ai_response,
            log_content=query,
            category="Commute",
        )

    if intent_tag == "search_query":
        query = attrs.get("query", "")
        return IntentResult(
            intent="search_query",
            ai_response=ai_response,
            log_content=query,
            category="Search",
        )

    if intent_tag == "weekly_review":
        return IntentResult(
            intent="weekly_review",
            ai_response=ai_response,
            log_content=None,
            category="WeeklyReview",
        )

    if intent_tag in ["lifelog_edit", "lifelog_heatmap"]:
        return IntentResult(
            intent=intent_tag,
            ai_response=ai_response,
            log_content=attrs.get("date"),
            category="LifeLogEditor" if intent_tag == "lifelog_edit" else "Heatmap",
        )

    if intent_tag == "web_url_query":
        return IntentResult(
            intent="web_url_query",
            ai_response=ai_response,
            log_content=None,
            category="System",
        )

    return IntentResult(
        intent="chat_only",
        ai_response=ai_response,
    )


def analyze_intent(
    prompt: str,
    history: list[dict[str, str]] | None = None,
    pending_log: dict[str, str] | None = None,
    gtd_path: str | None = None,
    call_ai_engine_func: Callable[[str, list[dict[str, str]] | None], str] | None = None,
) -> IntentResult:
    """
    사용자 입력의 의도를 판별하고 적합한 액션 및 응답을 도출합니다 (ADR-004, ADR-014, ADR-028, ADR-031, ADR-061).
    - 명시적 슬래시(/) 명령어: 결정론적 고속 실행 (_handle_slash_command)
    - 진행 중인 제안 승인/거절: 단순 승인/거절 토큰 처리
    - 그 외 모든 자연어 대화: 100% LLM AI 엔진을 거쳐 맥락 추론 및 의도 태그 파싱 수행
    """
    prompt_clean = prompt.strip()

    # 1. 이전 비서 제안에 대한 승인/거절 (pending_log) 판별
    if pending_log:
        reject_patterns = [
            r"(아니|아니야|아냐|됐어|필요\s*없|기록\s*하지\s*마|하지\s*마|취소|괜찮아|ㄴㄴ|no\b|cancel)",
            r"기록\s*(안\s*할래|안해)",
        ]
        for pattern in reject_patterns:
            if re.search(pattern, prompt_clean, re.IGNORECASE):
                return IntentResult(
                    intent="log_reject",
                    ai_response="네, 기록하지 않고 편안한 대화로만 기억해 둘게요! 😊 또 말씀해 주세요.",
                    log_content=None,
                    category=None,
                )

        has_context_backtrace = any(k in prompt_clean for k in ["아까", "방금", "이전", "앞서", "지난", "위에", "내가 말한", "말한 내용"])
        confirm_patterns = [
            r"^(?:응|어|네|예|그래|좋아|좋아요|좋습니다|부탁해|해줘|ㅇㅇ|yes|y|ok|sure|이대로|그대로|그렇게|맞아)(?:\s+(?:응|어|네|예|그래|좋아|좋아요|좋습니다|부탁해|해줘|ㅇㅇ|yes|y|ok|sure|이대로|그대로|그렇게|맞아))*[\.\!\?\s]*$",
            r"^(?:응|어|네|예|그래|좋아|좋아요|이대로|그대로|그렇게|\s|,)*\s*(?:기록|남겨|적어|등록|추가|반영)\s*(?:해줘|줘|주세요|부탁|부탁해|해)[\.\!\?\s]*$",
            r"^(?:이대로|그대로|그렇게)\s*(?:해줘|부탁해|진행해줘|기록해줘|부탁드립니다)[\.\!\?\s]*$",
        ]
        is_confirmed = not has_context_backtrace and any(re.search(pattern, prompt_clean, re.IGNORECASE) for pattern in confirm_patterns)
        if is_confirmed:
            content = pending_log.get("content", prompt_clean)
            cat = pending_log.get("category", "Daily Notes & Diary")
            gtd_task = pending_log.get("gtd_task")
            is_dual = pending_log.get("is_dual", False) or bool(gtd_task)
            if is_dual and gtd_task:
                return IntentResult(
                    intent="log_dual",
                    ai_response=(
                        f"검토해 주신 소중한 일상은 오늘 자 **[{cat}]**에 기록하고, "
                        f"실행 태스크(`- [ ] {gtd_task}`)는 **GTD 수집함(inbox.md)**에 등록 후 GitHub 동기화를 마쳤습니다! 📝📥✨"
                    ),
                    log_content=content,
                    category=cat,
                    gtd_task_content=gtd_task,
                    is_dual_log=True,
                )
            return IntentResult(
                intent="log_confirm",
                ai_response=f"오늘 자 라이프로그 **[{cat}]** 섹션에 '{content}' 내용을 예쁘게 기록하고 GitHub 동기화를 마쳤습니다! 📝✨",
                log_content=content,
                category=cat,
            )

    # 2. 명시적인 슬래시(/) 명령어 처리 (결정론적 고속 라우팅)
    if prompt_clean.startswith("/"):
        return _handle_slash_command(prompt_clean)

    # 3. 그 외 모든 자연어 입력: 100% LLM AI 엔진을 거쳐 의도 분석 및 답변 생성 (ADR-061)
    if call_ai_engine_func:
        llm_raw = call_ai_engine_func(prompt_clean, history)
    else:
        llm_raw = ""

    return _parse_llm_intent_result(llm_raw=llm_raw, prompt_clean=prompt_clean, history=history)
