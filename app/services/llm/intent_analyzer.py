from __future__ import annotations

import json
import os
import random
import re
from collections.abc import Callable
from dataclasses import dataclass

from app.config import get_now, settings
from app.services.llm.category_extractor import (
    detect_category,
    extract_actionable_task,
)


@dataclass
class IntentResult:
    """비서 에이전트의 의도 분석 및 응답 결과 데이터클래스."""

    intent: str  # "chat_only", "log_suggest", "log_confirm", "log_reject", "log_explicit", "log_dual", "task_briefing"
    ai_response: str
    log_content: str | None = None
    category: str | None = None
    gtd_task_content: str | None = None  # GTD inbox에 등록할 액션 태스크 (ADR-014)
    is_dual_log: bool = False  # 데일리 로그 + GTD 인박스 동시 기록 여부


def analyze_intent(
    prompt: str,
    history: list[dict[str, str]] | None = None,
    pending_log: dict[str, str] | None = None,
    gtd_path: str | None = None,
    call_ai_engine_func: Callable[[str, list[dict[str, str]] | None], str] | None = None,
) -> IntentResult:
    """
    사용자 입력의 의도를 판별하고 적합한 액션 및 응답을 생성합니다 (ADR-003, ADR-004, ADR-014, ADR-028, ADR-031, ADR-036).
    """
    prompt_clean = prompt.strip()

    # -------------------------------------------------------------
    # 1. 이전 비서 제안에 대한 승인/거절 (log_confirm / log_reject) 판별
    # -------------------------------------------------------------
    if pending_log:
        # (1-1) 거절 패턴 우선 검사
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

        # (1-2) 승인 패턴 검사 (단순 승인 또는 제안 초안 승인 지시어)
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

    # -------------------------------------------------------------
    # 1-0. 메타 피드백 / 항의 / 정정 발화 가드레일 (meta_feedback - ADR-031)
    # -------------------------------------------------------------
    meta_protest_patterns = [
        r"^(?:아니\s*)?(?:이미|벌써)?\s*.*?(?:있다면서|있잖아|했다면서|했잖아|말했잖아|그게\s*아니|왜\s*또|왜\s*새로|왜\s*등록|말한\s*건데|말한거야|말한건가|무슨\s*소리|이게\s*뭐야|그게\s*아닌데|누가\s*등록|등록하라는게\s*아니)",
        r"^(?:아니|그게\s*아니라)\s*.*?(?:완료|끝|해결|삭제|제거).*?(?:말한|한\s*건데|거야|잖아)",
        r".*?(?:있다면서|했다면서|말했잖아|그게\s*아니라|말한\s*건데|말한거야)[\?\!\.\s]*$",
    ]
    is_meta_protest = any(re.search(pat, prompt_clean, re.IGNORECASE) for pat in meta_protest_patterns)
    if is_meta_protest:
        if any(k in prompt_clean for k in ["완료", "끝", "해결", "체크", "다했"]):
            target_query = ""
            m_task = re.search(r"([가-힣a-zA-Z0-9\s]{2,25}?)\s*(?:완료했다고|완료한|끝났다고|해결했다고|완료)", prompt_clean)
            if m_task and len(m_task.group(1).strip()) >= 2:
                t_cand = m_task.group(1).strip()
                if not any(k in t_cand for k in ["아니", "인박스", "이미", "그래서", "말한"]):
                    target_query = t_cand
            if not target_query and history:
                for h in reversed(history):
                    if h.get("role") == "user":
                        prev_content = h.get("content", "").strip()
                        cleaned_prev = re.sub(r"(완료\s*gtd에\s*기록해|완료했어|완료|끝났어|gtd에\s*기록해|기록해)[\.\!\?\s]*$", "", prev_content).strip()
                        cleaned_prev = re.sub(r"[은는이가을를도]$", "", cleaned_prev).strip()
                        if len(cleaned_prev) >= 2 and not any(k in cleaned_prev for k in ["아니", "인박스", "이미", "/", "briefing", "schedule"]):
                            target_query = cleaned_prev
                            break

            return IntentResult(
                intent="task_complete",
                ai_response="",
                log_content=target_query,
                category="GTD",
            )
        elif any(k in prompt_clean for k in ["삭제", "제거", "빼", "지워"]):
            return IntentResult(
                intent="gtd_remove",
                ai_response="",
                log_content=prompt_clean,
                category="GTD",
            )
        else:
            return IntentResult(
                intent="chat_only",
                ai_response=(
                    "아, 제가 말씀하신 맥락을 오해하고 잘못 처리해 드렸던 것 같습니다. 죄송합니다! 🙇‍♂️\n\n"
                    "요청하시려던 작업이나 확인이 필요한 내용이 있다면 다시 편하게 말씀해 주세요. 즉시 의도에 맞게 챙겨드리겠습니다!"
                ),
                log_content=None,
                category=None,
            )

    # -------------------------------------------------------------
    # 2. 명시적 직접 기록 및 맥락 참조 기록 요청 (log_explicit - ADR-010)
    # -------------------------------------------------------------
    if prompt_clean.startswith("/log "):
        log_body = prompt_clean[5:].strip()
        cat = detect_category(log_body)
        return IntentResult(
            intent="log_explicit",
            ai_response=f"명령해 주신 내용을 오늘 자 라이프로그 **[{cat}]**에 즉시 기록하고 GitHub에 커밋했습니다! 📄🚀",
            log_content=log_body,
            category=cat,
        )

    # 2-1. 이전 대화 맥락 참조 기록 (ADR-010, ADR-012, ADR-028)
    record_action_pattern = r"(?:기록|적어|남겨|올려|저장|써|메모|넣어|추가|등록|반영|업데이트)\s*(?:해줘|줘|주세요|부탁|해|달라|달라구|하기|하자)"
    context_ref_pattern = r"(?:아까|방금|이전|앞서|지난|위|위의|위ㅡ|이|그)\s*(?:말한|한|이야기|대화|내용|글|것|거)"

    has_explicit_context_ref = bool(re.search(context_ref_pattern, prompt_clean)) or (
        any(k in prompt_clean for k in ["아까", "방금", "이전", "앞서"]) and any(k in prompt_clean for k in ["말", "이야기", "내용"])
    )
    has_record_action = bool(re.search(record_action_pattern, prompt_clean))

    stripped_directive = prompt_clean
    stripped_directive = re.sub(r"^(응|어|네|예|그래|좋아|좋아요|오케이|ok|yes)\s*", "", stripped_directive, flags=re.IGNORECASE)
    stripped_directive = re.sub(r"(오늘|오늘자|오늘의|내일|어제)?\s*(라이프\s*로그|로그|일기|다이어리|수집함|인박스)?\s*(?:에|로|을|를)?\s*", "", stripped_directive)
    stripped_directive = re.sub(r"(기록|적어|남겨|올려|저장|써|메모|넣어|추가|등록|반영|업데이트)\s*(해줘|줘|주세요|부탁해|해|달라|달라구)?\s*", "", stripped_directive)
    stripped_directive = re.sub(r"(이|그)?\s*(내용|이야기|글|것|거|말)?\s*(?:도|은|는|이|가)?\s*", "", stripped_directive)
    is_pure_directive = has_record_action and len(stripped_directive.strip()) <= 2

    if (has_explicit_context_ref or is_pure_directive) and has_record_action and history:
        command_phrases = ["기록해", "푸시", "확인", "동기화", "pull", "push", "sync", "/", "응"]
        previous_user_msg = next(
            (
                h["content"].strip()
                for h in reversed(history)
                if h.get("role") == "user"
                and len(h.get("content", "").strip()) > 8
                and not any(h.get("content", "").strip().startswith(cp) for cp in command_phrases)
            ),
            None,
        )
        if previous_user_msg:
            log_body = previous_user_msg
            cat = detect_category(f"{prompt_clean} {log_body}")
            snippet = log_body[:25] + "..." if len(log_body) > 25 else log_body
            is_gtd = any(k in prompt_clean.lower() for k in ["gtd", "인박스", "inbox", "수집함", "할일"])
            if is_gtd:
                gtd_task = extract_actionable_task(log_body)
                return IntentResult(
                    intent="log_explicit",
                    ai_response=f"이전 이야기에서 추출한 태스크(`- [ ] {gtd_task}`)를 **GTD 수집함(inbox.md)**에 등록하고 GitHub에 커밋했습니다! 📥🚀",
                    log_content=f"- [ ] {gtd_task}",
                    category="GTD Inbox",
                )
            return IntentResult(
                intent="log_explicit",
                ai_response=f"나누어 주신 소중한 이야기('{snippet}')를 오늘 자 라이프로그 **[{cat}]**에 기록하고 GitHub에 커밋했습니다! 🕯️📝",
                log_content=log_body,
                category=cat,
            )

    # 2-1-2. 문두 기록 지시어 처리 (ADR-028)
    front_record_pattern = (
        r"^(?:아니\s*)?(?:어제|오늘|오늘자|데일리)?\s*(?:자\s*)?(?:라이프\s*)?"
        r"(?:로그|일기|다이어리|gtd|인박스|수집함|할일)?\s*(?:에|로)?\s*"
        r"(?:이\s*내용|이\s*이야기|이\s*글|이거|내용)?\s*(?:을|를|도)?\s*"
        r"(?:기록해줘|적어줘|남겨줘|넣어줘|넣어달라구|넣어달라|추가해줘|올려줘|등록해줘|반영해줘|메모해줘)[:\s\n]+(.+)"
    )
    front_match = re.search(front_record_pattern, prompt_clean, re.DOTALL | re.IGNORECASE)
    if front_match:
        body = front_match.group(1).strip()
        is_ref_body = any(ref in body for ref in ["위 내용", "위의 내용", "이 내용", "그 내용", "위ㅡ내용"]) or len(body) < 5
        if is_ref_body and history:
            prev_msg = next(
                (
                    h["content"].strip()
                    for h in reversed(history)
                    if h.get("role") == "user"
                    and len(h.get("content", "").strip()) > 8
                    and not any(h.get("content", "").strip().startswith(cp) for cp in ["기록해", "푸시", "확인", "동기화", "pull", "push", "sync", "/", "응"])
                ),
                None,
            )
            if prev_msg:
                body = prev_msg

        if len(body) > 3:
            front_prefix = prompt_clean[:front_match.start(1)].lower()
            is_yesterday = "어제" in front_prefix
            is_gtd = any(k in front_prefix for k in ["gtd", "인박스", "inbox", "수집함", "할일"])
            date_label = "어제 자" if is_yesterday else "오늘 자"

            if is_gtd:
                gtd_task = extract_actionable_task(body)
                return IntentResult(
                    intent="log_explicit",
                    ai_response=f"요청하신 태스크(`- [ ] {gtd_task}`)를 **GTD 수집함(inbox.md)**에 등록하고 GitHub에 커밋했습니다! 📥🚀",
                    log_content=f"- [ ] {gtd_task}",
                    category="GTD Inbox",
                )
            else:
                cat = detect_category(body)
                return IntentResult(
                    intent="log_explicit",
                    ai_response=f"보내주신 소중한 일과와 감정을 {date_label} 라이프로그 **[{cat}]**에 즉시 기록하고 GitHub에 커밋했습니다! 📝✨",
                    log_content=body,
                    category=cat,
                )

    # -------------------------------------------------------------
    # 2-1-3. GTD 태스크 체크박스 완료 처리 (task_complete - ADR-027, ADR-031)
    # -------------------------------------------------------------
    prompt_lower = prompt_clean.lower()
    done_shortcuts = ["/done", "done", "1순위 완료", "1순위완료", "1순위 태스크 완료", "1순위 끝", "1순위 끝났어", "1번 완료", "탑 태스크 완료"]
    is_done_cmd = prompt_lower in done_shortcuts or prompt_lower.startswith("/done ")

    complete_gtd_record_pattern = (
        r"^(.*?)(?:은|는|이|가|도)?\s*(?:완료|해결|끝|체크)\s*(?:처리)?\s*(?:도|는|은)?\s*"
        r"(?:오늘\s*)?(?:자\s*)?(?:gtd|인박스|inbox|수집함|할일|next\s*actions)?\s*(?:에|로|도)?\s*"
        r"(?:기록해줘|기록해|적어줘|남겨줘|반영해줘|반영해|체크해줘|체크해|체크)[\.\!\?\s]*$"
    )
    complete_gtd_match = re.search(complete_gtd_record_pattern, prompt_clean, re.IGNORECASE)

    colloquial_complete_pattern = (
        r"^(.*?)(?:은|는|이|가|도)?\s*"
        r"(?:완료했어|완료함|완료|끝났어|끝냈어|끝냄|다했어|다했다|해결했어|해결함|해결|마쳤어|마침|해치웠어|체크해줘|체크함|체크)[\.\!\?\s]*$"
    )
    colloquial_match = re.search(colloquial_complete_pattern, prompt_clean, re.IGNORECASE)

    is_complete_target = False
    target_query = ""

    if is_done_cmd:
        is_complete_target = True
        if prompt_lower.startswith("/done "):
            target_query = prompt_clean[6:].strip()
    elif complete_gtd_match:
        is_complete_target = True
        target_query = complete_gtd_match.group(1).strip()
    elif colloquial_match and len(colloquial_match.group(1).strip()) <= 45:
        raw_target = colloquial_match.group(1).strip()
        daily_summary_keywords = ["오늘", "하루", "일과", "업무", "퇴근", "출근"]
        workout_keywords = ["헬스장", "스쿼트", "푸시업", "벤치프레스", "데드리프트", "런닝", "달리기", "러닝", "산책", "유산소", "웨이트", "운동"]
        words = raw_target.split()
        is_pure_summary = len(words) > 0 and all(k in daily_summary_keywords for k in words)
        is_workout_story = any(wk in raw_target for wk in workout_keywords)
        if not is_pure_summary and not is_workout_story and not any(k in raw_target for k in ["아니", "인박스", "이미"]):
            is_complete_target = True
            target_query = raw_target

    if is_complete_target:
        target_query = re.sub(r"^(응|어|네|예|그래|좋아|오늘|오늘자|자|gtd|인박스|할일|태스크)\s*", "", target_query).strip()
        target_query = re.sub(r"[은는이가을를도]$", "", target_query).strip()
        if target_query in ["1순위", "1번", "탑", "top", "첫번째", "태스크", "할일", "과제", ""]:
            target_query = ""
        return IntentResult(
            intent="task_complete",
            ai_response="",
            log_content=target_query,
            category="GTD",
        )

    # 2-2. 복합 기록 지시 (데일리 로그 + GTD 인박스 동시 기록 - ADR-014)
    dual_pattern = r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:데일리\s*)?(?:라이프\s*)?(?:로그\s*와|로그\s*랑|일기\s*와|일기\s*랑|다이어리\s*와|다이어리\s*랑)\s*(?:gtd\s*에?|할일\s*(?:에|에?도)?|인박스\s*에?|수집함\s*에?)\s*(?:둘\s*다|모두|함께|동시에)?\s*(?:에|로|을|를|도)?\s*(?:기록해줘|적어줘|남겨줘|넣어줘|추가해줘|올려줘|등록해줘|기록해|메모해줘)[\.\!\?\s]*$"
    dual_reverse_pattern = r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:gtd\s*와|gtd\s*랑|할일\s*과|할일\s*이랑|인박스\s*와|인박스\s*랑)\s*(?:데일리\s*)?(?:라이프\s*)?(?:로그\s*에?|일기\s*에?|다이어리\s*에?)\s*(?:둘\s*다|모두|함께|동시에)?\s*(?:에|로|을|를|도)?\s*(?:기록해줘|적어줘|남겨줘|넣어줘|추가해줘|올려줘|등록해줘|기록해|메모해줘)[\.\!\?\s]*$"

    dual_match = re.search(dual_pattern, prompt_clean, re.IGNORECASE) or re.search(dual_reverse_pattern, prompt_clean, re.IGNORECASE)
    if dual_match:
        cleaned_story = prompt_clean[:dual_match.start()].strip()
        cleaned_story = re.sub(r"^(응|어|네|예|그래|좋아|좋아요)\s*", "", cleaned_story).strip()
        if len(cleaned_story) > 3:
            gtd_task = extract_actionable_task(cleaned_story)
            cat = "Daily Notes & Diary"
            return IntentResult(
                intent="log_dual",
                ai_response=(
                    f"소중한 일상 이야기는 오늘 자 **[{cat}]**에 기록하고, "
                    f"실행 태스크(`- [ ] {gtd_task}`)는 **GTD 수집함(inbox.md)**에 등록했습니다! 📝📥✨"
                ),
                log_content=cleaned_story,
                category=cat,
                gtd_task_content=gtd_task,
                is_dual_log=True,
            )

    # 2-3. 단일 후미 기록 명령
    single_end_pattern = r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:데일리\s*)?(?:라이프\s*)?(?:로그|일기|다이어리|gtd|인박스|수집함|할일)?\s*(?:에|로|을|를|도)?\s*(?:기록해줘|적어줘|남겨줘|넣어줘|추가해줘|올려줘|등록해줘|기록해|메모해줘)[\.\!\?\s]*$"
    single_end_match = re.search(single_end_pattern, prompt_clean, re.IGNORECASE)
    if single_end_match and len(prompt_clean[:single_end_match.start()].strip()) > 3:
        cleaned_body = prompt_clean[:single_end_match.start()].strip()
        cleaned_body = re.sub(r"^(응|어|네|예|그래|좋아|좋아요)\s*", "", cleaned_body).strip()
        matched_suffix = single_end_match.group(0).lower()

        if any(k in matched_suffix for k in ["gtd", "인박스", "inbox", "수집함", "할일"]):
            if any(w in cleaned_body for w in ["완료", "끝", "해결", "체크"]):
                pure_task = re.sub(r"(완료|끝|해결|체크)[\.\!\?\s]*$", "", cleaned_body).strip()
                pure_task = re.sub(r"[은는이가을를도]$", "", pure_task).strip()
                return IntentResult(
                    intent="task_complete",
                    ai_response="",
                    log_content=pure_task,
                    category="GTD",
                )
            gtd_task = extract_actionable_task(cleaned_body)
            return IntentResult(
                intent="log_explicit",
                ai_response=f"요청하신 태스크(`- [ ] {gtd_task}`)를 **GTD 수집함(inbox.md)**에 등록하고 GitHub에 커밋했습니다! 📥🚀",
                log_content=f"- [ ] {gtd_task}",
                category="GTD Inbox",
            )
        else:
            cat = detect_category(cleaned_body)
            return IntentResult(
                intent="log_explicit",
                ai_response=f"보내주신 소중한 일과와 감정을 오늘 자 라이프로그 **[{cat}]**에 즉시 기록하고 GitHub에 커밋했습니다! 📝✨",
                log_content=cleaned_body,
                category=cat,
            )

    # 2-4. 문장 중간 기록 지시어 처리
    explicit_match = re.search(
        r"(.*?)(?:을|를)?\s*(?:기록해줘|일기에\s*적어줘|로그에\s*남겨줘|기록해)(.*)",
        prompt_clean,
        re.DOTALL,
    )
    if explicit_match:
        main_part = explicit_match.group(1).strip()
        extra_part = explicit_match.group(2).strip()
        cleaned_main = re.sub(r"^(응|어|네|예|그래|좋아|좋아요)\s*", "", main_part)
        cleaned_main = re.sub(r"^(오늘|오늘자|라이프로그|로그|일기)?\s*(?:에|로)?\s*", "", cleaned_main).strip()
        if len(cleaned_main) > 2 and not any(w in main_part for w in ["아까", "방금", "이전"]):
            log_body = f"{main_part} {extra_part}".strip() if extra_part else main_part
            cat = detect_category(log_body)
            return IntentResult(
                intent="log_explicit",
                ai_response=f"요청하신 '{main_part}' 내용을 오늘 자 **[{cat}]**에 기록하고 GitHub에 커밋했습니다! 📄✨",
                log_content=log_body,
                category=cat,
            )

    # 2-4. GTD 태스크 삭제/제거 의도 (gtd_remove - ADR-020)
    remove_triggers = ["제거", "삭제", "빼줘", "빼", "지워", "지워줘", "제외", "제외해", "완료 처리", "해결 완료"]
    has_remove_trigger = any(rt in prompt_clean for rt in remove_triggers)
    if has_remove_trigger and any(k in prompt_clean for k in ["는", "도", "은", "를", "을", "에서", "할일", "태스크", "인박스", "tiara", "아젠다", "보고", "지원", "시간", "gtd", "케어"]):
        return IntentResult(
            intent="gtd_remove",
            ai_response="",
            log_content=prompt_clean,
            category="GTD",
        )

    # 2-4-2. 웹 대시보드 / 접속 URL 질의 (web_url_query)
    url_exact = ["/url", "/web", "/link", "/tunnel", "웹주소", "웹링크", "접속주소", "접속링크"]
    is_url_cmd = prompt_clean.lower() in url_exact
    url_patterns = [
        r"^(?:웹|대시보드|콘솔|접속)?\s*(?:주소|링크|url)\s*(?:알려줘|알려|어디야|뭐야|보여줘)?[\.\!\?\s]*$",
        r"(?:웹\s*대시보드|웹\s*콘솔|접속\s*주소|외부\s*링크)\s*(?:알려줘|알려|확인|링크)",
    ]
    is_url_match = is_url_cmd or any(re.search(pat, prompt_clean.lower(), re.IGNORECASE) for pat in url_patterns)
    if is_url_match and not any(k in prompt_clean for k in ["기록", "적어", "커밋", "삭제"]):
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

    # 2-5. Git 커밋 명령 (repo_commit - ADR-020)
    commit_exact = ["/commit", "commit", "커밋", "커밋해", "커밋해줘", "커밋도 해줘", "커밋도해줘", "커밋하자", "커밋해야지", "깃 커밋", "git commit", "커밋 부탁", "커밋 부탁해", "커밋 진행해"]
    commit_patterns = [
        r"^(?:깃|git)?\s*(?:커밋|commit)\s*(?:해줘|해|줘|주세요|부탁|하자|해야지|진행|해라)?[\.\!\?\s]*$",
        r"(?:정리된\s*(?:것|내용|상태)?|방금\s*(?:작업|내용)?)\s*(?:커밋|commit)\s*(?:해줘|해|줘|주세요|하자|해야지)",
    ]
    is_commit_cmd = prompt_clean.lower() in commit_exact or any(re.search(pat, prompt_clean, re.IGNORECASE) for pat in commit_patterns)
    if is_commit_cmd:
        return IntentResult(
            intent="repo_commit",
            ai_response="",
            log_content=None,
            category="Git",
        )

    # -------------------------------------------------------------
    # 3. GTD 레포 원격 푸시 및 상태/원격지 확인 (repo_push - ADR-011, ADR-020)
    # -------------------------------------------------------------
    is_pushup = any(w in prompt_clean.lower() for w in ["푸시업", "pushup", "push-up", "push up"])

    is_push_query = any(q in prompt_clean for q in [
        "어디다 푸시", "어디로 푸시", "어디에 푸시", "푸시 어디", "어디 푸시",
        "푸시 주소", "푸시 저장소", "푸시 레포", "레포 주소", "저장소 주소",
        "푸시 됐어", "푸시 됐니", "푸시 되었", "푸시된 거 맞아", "푸시된거 맞아",
        "어디로 push", "어디다 push"
    ])

    push_exact_words = [
        "/push", "push", "푸시", "푸시해", "푸시해줘", "푸시도 해줘", "푸시도해줘", "푸시도",
        "푸시해야지", "푸시도해야지", "푸시도 해야지", "푸시하자", "푸시해야돼", "푸시도 해",
        "푸시 부탁", "푸시 부탁해", "깃 푸시", "깃 푸시해줘", "git push", "깃푸시",
        "푸시 확인", "푸시 확인해줘", "푸시 다시 해줘", "푸시해라", "푸시 진행해",
        "올려야지", "올려줘", "깃허브로 올려", "깃허브에 올려", "원격으로 올려"
    ]
    is_explicit_push = prompt_clean.lower() in push_exact_words

    push_action_patterns = [
        r"(?:깃|git|원격|github|저장소|gtd|커밋|로그|내용|기록)?\s*(?:푸시|push)\s*(?:도\s*)?(?:해줘|해|줘|주세요|부탁|확인|다시|진행|하자|해야지|해야돼|해야지\?|했어\?|된거야\?|한거야\?)",
        r"(?:푸시|push)\s*(?:가|도|를|은)?\s*(?:안\s*됐|실패|누락|확인|다시|됐어|해줘|부탁|해야지|해야돼|하자|해)",
        r"(?:원격|깃허브|github)\s*(?:저장소)?(?:에|로)?\s*(?:올려줘|푸시해줘|반영해줘|보내줘|올려야지)",
    ]
    has_push_action = any(re.search(pat, prompt_clean, re.IGNORECASE) for pat in push_action_patterns)

    if not is_pushup and (is_explicit_push or has_push_action or is_push_query):
        return IntentResult(
            intent="repo_push",
            ai_response="",
            log_content="query" if is_push_query else "push",
            category="Git",
        )

    # -------------------------------------------------------------
    # 4. GTD 레포 원격 동기화 및 최신화 (repo_sync / repo_sync_and_briefing - ADR-009)
    # -------------------------------------------------------------
    sync_triggers = ["최신화", "동기화", "pull", "sync", "가져와"]
    if "업데이트" in prompt_clean.lower() and not any(k in prompt_clean for k in ["내용", "이야기", "기록", "적어", "넣어", "메모", "위 ", "이 ", "위ㅡ"]):
        sync_triggers.append("업데이트")
    has_sync = any(st in prompt_clean.lower() for st in sync_triggers)

    briefing_triggers = [
        "해야할 일", "해야 할 일", "할 일", "할일", "투두", "todo", "일정", "스케줄",
        "gtd", "다음 행동", "수집함", "인박스", "태스크", "스케쥴"
    ]
    action_triggers = [
        "정리", "알려", "보여", "뭐 있", "확인", "브리핑", "요약", "체크", "목록",
        "리스트", "뭐 해야", "어떤 거", "어떻게 돼", "뭐할까", "뭐하지", "현황", "다시 알려"
    ]
    briefing_request_triggers = [
        "알려", "정리", "보여", "브리핑", "요약", "보고", "체크", "어때", "어떻게",
        "해야할 일", "해야 할 일", "할 일", "할일", "투두", "일정", "스케줄", "다음 행동"
    ]

    if prompt_clean.lower() == "/sync" or (has_sync and any(k in prompt_clean.lower() for k in ["레포", "gtd", "저장소", "git", "깃"])):
        if any(brt in prompt_clean.lower() for brt in briefing_request_triggers):
            return IntentResult(
                intent="repo_sync_and_briefing",
                ai_response="",
                log_content=None,
                category="GTD",
            )
        return IntentResult(
            intent="repo_sync",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    # -------------------------------------------------------------
    # 4-0. 일일 로그 / GTD 파일 기록 여부 및 상태 질의 (log_status_inspect - ADR-028)
    # -------------------------------------------------------------
    status_patterns = [
        r"(?:오늘|오늘자|데일리)?\s*(?:라이프\s*)?(?:로그|일기|다이어리|기록|파일)?\s*(?:에|로)?\s*(?:기록했어|적었어|남겼어|썼어|올렸어|들어갔어|반영됐어|반영된거야|기록된거야|기록된\s*거\s*맞아|기록된거\s*맞아|기록\s*됐어|기록\s*됐니|기록됐니|적혔어|적힌거야|저장됐어|저장했어|기록된건가)[\?\.\!\s]*$",
        r"^(?:오늘|오늘자|오늘의|데일리)?\s*(?:라이프\s*)?(?:기록|일기|로그)\s*(?:확인|점검|체크|상태|확인해줘)[\?\.\!\s]*$",
        r"^(?:오늘|오늘자|오늘의|데일리)?\s*(?:라이프\s*)?(?:기록|일기|로그)\s*(?:됐어|된거야|된\s*건가|했어|한거야)[\?\.\!\s]*$",
        r"^(?:오늘\s*)?기록\s*했어[\?\.\!\s]*$",
        r"^(?:오늘\s*)?기록\s*됐어[\?\.\!\s]*$",
        r"^(?:오늘\s*)?일기\s*확인해줘[\?\.\!\s]*$",
        r"^(?:오늘\s*)?로그\s*확인해줘[\?\.\!\s]*$",
    ]
    is_status_inspect = any(re.search(pat, prompt_lower, re.IGNORECASE) for pat in status_patterns)
    if is_status_inspect and not any(k in prompt_lower for k in ["기록해줘", "적어줘", "남겨줘", "올려줘", "저장해줘", "써줘", "삭제", "제거", "푸시"]):
        return IntentResult(
            intent="log_status_inspect",
            ai_response="",
            log_content=None,
            category="LifeLog",
        )

    # -------------------------------------------------------------
    # 4-1. 오늘 일일 로그 / GTD 파일 직접 조회 숏컷 (ADR-022)
    # -------------------------------------------------------------
    gtd_keywords = ["gtd", "인박스", "inbox", "수집함", "할일", "next_actions", "다음 행동"]
    log_keywords = ["오늘 로그", "오늘자 로그", "오늘의 로그", "오늘 일기", "오늘자 일기", "데일리 로그", "데일리로그", "오늘 기록"]

    is_composite_shortcut = prompt_lower in ["/gtd-today", "/today-gtd", "/all-log"]
    has_both_targets = any(gk in prompt_lower for gk in gtd_keywords) and any(lk in prompt_lower for lk in log_keywords)
    read_inspect_triggers = ["읽어", "보여", "확인", "열어", "조회", "출력", "상태", "현황", "내용"]

    if is_composite_shortcut or (has_both_targets and any(rit in prompt_lower for rit in read_inspect_triggers)):
        return IntentResult(
            intent="gtd_and_log_inspect",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    # 오늘 일일 로그 직접 조회
    is_today_shortcut = prompt_lower in ["/today", "/daily", "today", "daily"]
    today_log_patterns = [
        r"^(?:오늘|오늘자|오늘의|데일리)\s*(?:라이프\s*)?(?:로그|일기|기록)\s*(?:보여줘|보여|읽어줘|읽어|확인|열어줘|열어|출력|조회|알려줘|어떻게\s*돼|내용)?[\.\!\?\s]*$",
        r"(?:오늘|오늘자|오늘의)\s*(?:작성된|기록된)?\s*(?:로그|일기|기록|다이어리)\s*(?:보여줘|읽어줘|열어줘|확인해줘|조회)",
    ]
    is_today_log_inspect = is_today_shortcut or any(re.search(pat, prompt_lower, re.IGNORECASE) for pat in today_log_patterns)
    if is_today_log_inspect and not has_record_action:
        return IntentResult(
            intent="daily_log_inspect",
            ai_response="",
            log_content=None,
            category="LifeLog",
        )

    # GTD 파일 직접 조회
    is_gtd_shortcut = prompt_lower in ["/gtd", "/inbox", "gtd", "inbox"]
    gtd_file_patterns = [
        r"^(?:gtd|인박스|inbox|수집함)\s*(?:파일|원본|내용)?\s*(?:보여줘|보여|읽어줘|읽어|확인|열어줘|열어|출력|조회)?[\.\!\?\s]*$",
        r"(?:gtd|inbox|인박스|next_actions|수집함|다음\s*행동)\s*(?:파일|문서|원본|마크다운)?\s*(?:읽어줘|읽어|보여줘|보여|확인해줘|열어줘|출력)",
    ]
    is_gtd_inspect = is_gtd_shortcut or any(re.search(pat, prompt_lower, re.IGNORECASE) for pat in gtd_file_patterns)
    if is_gtd_inspect and not has_record_action and not has_remove_trigger:
        return IntentResult(
            intent="gtd_inspect",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    # GTD 마감일 및 D-Day 현황 직접 조회 (ADR-042)
    is_dday_shortcut = prompt_lower in ["/dday", "/deadline", "dday", "deadline", "디데이"]
    dday_patterns = [
        r"^(?:gtd\s*)?(?:마감일|마감\s*일정|마감\s*과제|마감\s*태스크|마감|기한|d-?day|디데이)\s*(?:현황|목록|리포트|확인|알려줘|알려|보여줘|보여|조회|체크)?[\.\!\?\s]*$",
        r"(?:마감일|마감\s*일정|d-?day|디데이|기한)\s*(?:현황|목록|리포트|확인|알려|보여|조회|체크|어떻게|뭐|있어)",
        r"(?:마감\s*임박|기한\s*초과|오늘\s*마감)",
    ]
    is_dday_inspect = is_dday_shortcut or any(re.search(pat, prompt_lower, re.IGNORECASE) for pat in dday_patterns)
    if is_dday_inspect and not has_record_action and not has_remove_trigger:
        return IntentResult(
            intent="dday_inspect",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    # 과거 라이프로그 & GTD 고속 검색 (ADR-043)
    is_search_cmd = prompt_lower.startswith(("/search", "/find", "/검색", "/찾기"))
    search_query_kw = None

    if is_search_cmd:
        parts = prompt.strip().split(maxsplit=1)
        search_query_kw = parts[1].strip() if len(parts) > 1 else ""
    elif not has_record_action and not has_remove_trigger:
        search_nlp_match = re.search(
            r"^(?:(?:과거|이전|예전|지난|옛날|라이프로그|일기|로그|gtd)\s*(?:에서|의)?\s*)?"
            r"(.+?)\s*"
            r"(?:검색해줘|검색해|검색|찾아줘|찾아봐|찾아|있나\s*찾아줘|있나\s*찾아봐|어디\s*적었지|어디\s*있지)[\.\!\?\s]*$",
            prompt.strip(),
            re.IGNORECASE,
        )
        if search_nlp_match:
            extracted = search_nlp_match.group(1).strip()
            extracted = re.sub(r"^(?:과거|이전|예전|지난|라이프로그|일기|로그|gtd)\s*(?:에서|의)?\s*", "", extracted, flags=re.IGNORECASE).strip()
            extracted = re.sub(r"(?:내용|기록|일지|메모|정보)\s*$", "", extracted).strip()
            if extracted and len(extracted) >= 1:
                search_query_kw = extracted

    if search_query_kw is not None and not has_record_action:
        return IntentResult(
            intent="search_query",
            ai_response="",
            log_content=search_query_kw,
            category="Search",
        )

    # 주간 결산 회고 리포트 (ADR-043)
    is_weekly_shortcut = prompt_lower in ["/weekly", "/review", "/주간", "/주간결산", "/주간회고", "weekly", "주간결산", "주간회고"]
    weekly_patterns = [
        r"^(?:왓슨\s*)?(?:주간\s*결산|주간\s*회고|주간\s*리포트|주간\s*보고|주간\s*통계|이번\s*주\s*결산|이번\s*주\s*회고|이번\s*주\s*돌아보기|한\s*주\s*돌아보기|한\s*주\s*정리|이번주\s*결산|이번주\s*회고)\s*(?:해줘|알려줘|보여줘|부탁해|해|해봐)?[\.\!\?\s]*$",
    ]
    is_weekly_review = is_weekly_shortcut or any(re.search(pat, prompt_lower, re.IGNORECASE) for pat in weekly_patterns)
    if is_weekly_review and not has_record_action and not has_remove_trigger:
        return IntentResult(
            intent="weekly_review",
            ai_response="",
            log_content=None,
            category="WeeklyReview",
        )

    # Vision AI 사진 분석 (ADR-044)
    if prompt_lower.startswith(("/vision", "/photo", "/이미지", "/사진")):
        parts = prompt.strip().split(maxsplit=2)
        target_path = parts[1].strip() if len(parts) > 1 else ""
        caption = parts[2].strip() if len(parts) > 2 else ""
        return IntentResult(
            intent="vision_inspect",
            ai_response="",
            log_content=json.dumps({"path": target_path, "caption": caption}, ensure_ascii=False),
            category="Vision",
        )

    # 마크다운 일일 로그 인플레이스 편집기 (ADR-045)
    is_edit_cmd = prompt_lower.startswith(("/edit", "/editor", "/수정", "/편집"))
    is_edit_nlp = any(k in prompt_lower for k in ["일기 편집", "로그 편집", "로그 수정", "일기 수정", "마크다운 편집", "일기 고쳐", "로그 고쳐"])
    if (is_edit_cmd or is_edit_nlp) and not has_record_action and not has_remove_trigger:
        parts = prompt.strip().split(maxsplit=1)
        target_date = parts[1].strip() if (is_edit_cmd and len(parts) > 1) else ""
        return IntentResult(
            intent="lifelog_edit",
            ai_response="",
            log_content=target_date,
            category="LifeLogEditor",
        )

    # 라이프로그 잔디 요약 질의 (ADR-045)
    is_heatmap_cmd = prompt_lower.startswith(("/heatmap", "/잔디", "/기여도"))
    is_heatmap_nlp = any(k in prompt_lower for k in ["잔디 확인", "잔디 보여줘", "히트맵", "스트릭", "기록 스트릭", "연속 기록 몇일"])
    if (is_heatmap_cmd or is_heatmap_nlp) and not has_record_action and not has_remove_trigger:
        return IntentResult(
            intent="lifelog_heatmap",
            ai_response="",
            log_content=None,
            category="Heatmap",
        )

    # (C) 출근길 날씨·미세먼지·버스 브리핑 설정 및 실시간 날씨 질의 (ADR-030, ADR-033)
    # (C-1) 동네 설정 및 스마트 지오코딩 자동 매핑 (ADR-034)
    is_loc_cmd = prompt_lower.startswith(("/location", "/동네", "/지역"))
    is_loc_nlp = (
        any(k in prompt_lower for k in ["동네", "지역", "거주지", "우리동네", "우리 동네"]) and
        any(v in prompt_lower for v in ["설정", "변경", "바꿔", "등록", "어디", "확인", "인데", "이야", "바꿀", "해줘", "맞아"])
    )
    if is_loc_cmd or is_loc_nlp:
        loc_query = ""
        if is_loc_cmd:
            parts = prompt.strip().split(maxsplit=1)
            if len(parts) > 1:
                loc_query = parts[1].strip()
        else:
            loc_query = prompt.strip()

        is_inspect_only = not loc_query or (
            any(q in prompt_lower for q in ["어디야", "어디로", "어디에", "어디", "확인", "현재", "어떻게"]) and
            not any(s in prompt_lower for s in ["으로 설정", "로 설정", "으로 바꿔", "로 바꿔", "으로 변경", "로 변경", "인데", "설정해", "바꿔줘", "등록해", "해줘"])
        )

        return IntentResult(
            intent="location_set" if not is_inspect_only else "location_inspect",
            ai_response="",
            log_content=loc_query if not is_inspect_only else None,
            category="Commute",
        )

    is_commute_cmd = prompt_lower.startswith(("/commute", "/bus", "/weather", "/air"))
    is_commute_nlp = any(k in prompt_lower for k in ["출근길", "출근 버스", "버스 언제", "버스 도착", "버스 정보", "우리 동네 날씨", "우리지역 날씨", "출근길 날씨"])
    has_greeting = any(g in prompt_lower for g in ["안녕", "반가워", "하이", "좋은 아침"])
    is_bus_info_query = any(k in prompt_lower for k in [
        "출근 버스", "버스 언제", "버스 도착", "버스 정보", "버스 시간", "버스 잔여", "버스 타임", "몇 분 뒤 와", "몇분 뒤 와"
    ]) or prompt_lower in ["/bus", "/버스", "버스"] or prompt_lower.startswith("/bus")
    is_weather_info_query = any(k in prompt_lower for k in ["날씨 브리핑", "날씨 정보", "미세먼지 정보", "미세먼지 수치", "대기질 정보", "오늘 날씨 정보", "날씨랑 미세먼지"]) or (
        any(k in prompt_lower for k in ["미세먼지", "초미세먼지", "대기질"]) and any(q in prompt_lower for q in ["어때", "알려", "확인", "보여", "수치", "상태"])
    )
    if (is_commute_cmd or is_commute_nlp or is_weather_info_query or is_bus_info_query) and not has_greeting:
        is_preview = any(k in prompt_lower for k in [
            "test", "preview", "미리보기", "테스트", "지금"
        ])
        if is_bus_info_query and not is_preview:
            sub_mode = "bus"
        elif is_weather_info_query or "weather" in prompt_lower:
            sub_mode = "weather"
        elif is_preview:
            sub_mode = "preview"
        else:
            sub_mode = "status"

        return IntentResult(
            intent="commute_inspect",
            ai_response="",
            log_content=sub_mode,
            category="Commute",
        )

    # -------------------------------------------------------------
    # 4-2. GTD 할 일 / 일정 / 브리핑 요청 (task_briefing - ADR-008, ADR-024, ADR-025)
    # -------------------------------------------------------------
    is_schedule_cmd = prompt_lower in ["/schedule", "/briefing schedule", "스케줄", "스케쥴", "브리핑 스케줄"]
    is_schedule_nlp = any(k in prompt_lower for k in ["브리핑", "일정", "회고"]) and any(s in prompt_lower for s in ["스케줄", "스케쥴", "몇 시", "몇시", "시간", "언제", "스케쥴링", "스케줄링"])
    if is_schedule_cmd or is_schedule_nlp or ("스케" in prompt_lower and any(q in prompt_lower for q in ["몇 시", "몇시", "언제", "확인", "보여", "알려", "어떻게"])):
        return IntentResult(
            intent="briefing_schedule_inspect",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    is_morning_cmd = prompt_lower in ["/briefing morning", "/briefing am", "/briefing 아침", "아침 브리핑", "모닝 브리핑", "출근 브리핑"]
    is_morning_nlp = any(m in prompt_lower for m in ["아침", "모닝", "출근"]) and any(b in prompt_lower for b in ["브리핑", "일정", "할일", "시작", "정리"])
    if is_morning_cmd or is_morning_nlp:
        return IntentResult(
            intent="task_briefing_morning",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    is_evening_cmd = prompt_lower in ["/briefing evening", "/briefing pm", "/briefing 저녁", "/briefing 회고", "저녁 브리핑", "이브닝 브리핑", "퇴근 브리핑", "오늘 회고", "저녁 정산"]
    is_evening_nlp = any(e in prompt_lower for e in ["저녁", "이브닝", "퇴근", "회고", "정산", "마무리"]) and any(b in prompt_lower for b in ["브리핑", "일정", "할일", "회고", "정리", "정산", "마무리"])
    if is_evening_cmd or is_evening_nlp:
        return IntentResult(
            intent="task_briefing_evening",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    is_briefing_cmd = prompt_lower in ["/briefing", "briefing", "브리핑"]
    if is_briefing_cmd or (any(bt in prompt_lower for bt in briefing_triggers) and any(at in prompt_lower for at in action_triggers)):
        return IntentResult(
            intent="task_briefing",
            ai_response="",
            log_content=None,
            category="GTD",
        )

    # -------------------------------------------------------------
    # 4. 일과/사건/생각 감지 및 사전 검토 초안 제안 (log_suggest - ADR-004, ADR-029, ADR-036)
    # -------------------------------------------------------------
    time_str = get_now().strftime("%H:%M")
    date_str = get_now().strftime("%Y-%m-%d")

    negative_feedback_patterns = [
        r"필요\s*(?:가\s*)?없",
        r"안\s*(?:사도|해도|가도|먹어도|시켜도|봐도|있어도)\s*(?:돼|됨|된다|괜찮)",
        r"(?:살|할|갈|먹을|시킬)\s*필요\s*없",
        r"(?:선물\s*받아|선물받아|이미\s*있|벌써\s*있)",
        r"(?:취소|환불|철회|삭제|제거|빼|지워|제외)",
        r"(?:어때|어떨까|어떻게|할까|할까\?|\?$)",
    ]
    is_negative_or_feedback = any(re.search(pat, prompt_clean, re.IGNORECASE) for pat in negative_feedback_patterns)

    if not is_negative_or_feedback:
        # (A) 명확한 운동 수행/완료 서사 진술 (Workout & Health)
        workout_terms = [
            r"운동\s*(?:완료|성공|했어|다녀왔|끝)",
            r"헬스\s*(?:장\s*)?(?:다녀왔|에서|완료|성공|했어)",
            r"러닝\s*(?:\d+km\s*)?(?:뛰|달렸|완료|성공|했어)",
            r"달리기\s*(?:\d+km\s*)?(?:뛰|달렸|완료|성공|했어)",
            r"스쿼트\s*(?:\d+kg\s*)?(?:성공|완료|했어)",
            r"벤치\s*(?:프레스\s*)?(?:\d+kg\s*)?(?:성공|완료|했어)",
            r"풀업\s*(?:\d+개\s*)?(?:성공|완료|했어)",
            r"푸시업\s*(?:\d+개\s*)?(?:성공|완료|했어)",
            r"\bpt\s*(?:받았|받고|다녀왔|완료|성공)",
            r"산책\s*(?:\d+분\s*)?(?:다녀왔|하고\s*왔|했어)",
            r"수영\s*(?:다녀왔|하고\s*왔|완료|했어)",
            r"(?<![필중가])요가\s*(?:수업\s*)?(?:다녀왔|하고\s*왔|완료|했어)",
            r"\d+만\s*보\s*(?:달성|걸었|완료)",
        ]
        has_workout_narrative = any(re.search(t, prompt_clean, re.IGNORECASE) for t in workout_terms) or is_pushup

        if has_workout_narrative:
            cat = "Workout & Health"
            ai_response = (
                f"건강을 챙기시는 모습이 정말 멋지십니다! 🏋️ 오늘 운동 기록({cat})에 아래 초안대로 **기록해 둘까요?** 📝\n\n"
                f"---\n"
                f"### 📝 라이프로그 초안 (`logs/daily/{date_str}.md` [{cat}])\n"
                f"- [{time_str}] {prompt_clean}\n"
                f"---\n"
                f"👉 **'응'** 또는 아래 **[✅ 응, 기록해줘]** 버튼을 눌러주시면 즉시 GitHub에 커밋·푸시합니다! ✨"
            )
            return IntentResult(
                intent="log_suggest",
                ai_response=ai_response,
                log_content=prompt_clean,
                category=cat,
            )

        # (B) 일상, 가족, 감정, 식사, 케어 등 삶의 기록 사전 검토 제안 (ADR-029)
        narrative_actions = ["끓였어", "차렸어", "먹었어", "다녀왔어", "갔다왔어", "퇴근하고", "수술하고", "진료받고", "치료받고", "간호했어"]
        has_narrative_action = any(act in prompt_clean for act in narrative_actions)
        life_subjects = ["아내", "와이프", "남편", "가족", "아이", "아기", "부모님", "미역국", "소파술", "병원"]
        has_life_subject = any(sub in prompt_clean for sub in life_subjects)

        if has_narrative_action and has_life_subject and len(prompt_clean) >= 6:
            cat = "Daily Notes & Diary"
            is_comfort_needed = any(k in prompt_clean for k in ["수술", "병원", "초음파", "심장", "슬픔", "아픔", "눈물", "간호", "케어", "미역국"])
            intro = (
                "마음이 참 무겁고 애틋하셨을 텐데 소중한 이야기를 나누어 주셔서 감사합니다. 곁에서 두 분을 진심으로 응원합니다. 🕯️\n\n"
                if is_comfort_needed
                else "소중한 일상과 마음을 나누어 주셔서 감사합니다. 😊\n\n"
            )

            gtd_task = extract_actionable_task(prompt_clean)
            has_actionable = any(k in prompt_clean for k in ["챙기", "예약", "사기", "신청", "준비", "방문", "확인", "돌보"]) and len(gtd_task) > 4

            preview_lines = [
                f"### 📝 라이프로그 초안 (`logs/daily/{date_str}.md` [{cat}])",
                f"- [{time_str}] {prompt_clean}",
            ]
            if has_actionable:
                preview_lines.extend([
                    "",
                    "### 📥 GTD 수집함 초안 (`gtd/inbox.md`)",
                    f"- [ ] {gtd_task}",
                ])

            preview_body = "\n".join(preview_lines)
            ai_response = (
                f"{intro}"
                f"말씀해주신 소중한 일과를 아래와 같이 정리했습니다. 이대로 **기록해 둘까요?** 📝\n\n"
                f"---\n"
                f"{preview_body}\n"
                f"---\n"
                f"👉 **'응'** 또는 아래 **[✅ 응, 기록해줘]** 버튼을 눌러주시면 즉시 GitHub에 커밋·푸시합니다! ✨"
            )
            return IntentResult(
                intent="log_suggest",
                ai_response=ai_response,
                log_content=prompt_clean,
                category=cat,
                gtd_task_content=gtd_task if has_actionable else None,
                is_dual_log=has_actionable,
            )

    # -------------------------------------------------------------
    # 5. 빠른 응답 패턴 (Fast-Path)
    # -------------------------------------------------------------
    if re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean) or ("숫자" in prompt_clean and "골라" in prompt_clean):
        match = re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean)
        if match:
            min_val, max_val = int(match.group(1)), int(match.group(2))
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            chosen = random.randint(min_val, max_val)
            return IntentResult(
                intent="chat_only",
                ai_response=f"제가 **{min_val}부터 {max_val} 범위**에서 고른 숫자는 **{chosen}**입니다! 🎲 마음에 드시나요?",
            )
        else:
            chosen = random.randint(1, 30)
            return IntentResult(
                intent="chat_only",
                ai_response=f"제가 고른 숫자는 **{chosen}**입니다! 🎲 마음에 드시나요?",
            )

    if re.search(r"왜\s*(\d+).*?(골랐|선택)", prompt_clean) or ("왜" in prompt_clean and "골랐" in prompt_clean):
        num_match = re.search(r"(\d+)", prompt_clean)
        num_str = num_match.group(1) if num_match else "그 숫자"
        return IntentResult(
            intent="chat_only",
            ai_response=(
                f"제가 {num_str}을 고른 이유는, 수많은 숫자 중에서 가장 반짝이고 오늘 사용자님께 "
                f"특별한 행운과 활력을 불어넣어 줄 것 같은 기운이 느껴졌기 때문이에요! 🎲✨\n"
                f"나누어떨어지지 않는 독보적인 매력도 있고요. 마음에 드셨길 바랍니다! 😊"
            ),
        )

    # -------------------------------------------------------------
    # 6. 지능형 AI 엔진 대화 (AGY / Gemini Bridge)
    # -------------------------------------------------------------
    if call_ai_engine_func:
        ai_response = call_ai_engine_func(prompt_clean, history)
    else:
        ai_response = "네, 사용자님 말씀 잘 듣고 있습니다! 😊 오늘 하루 있었던 일과나 나누고 싶은 생각, 혹은 정리할 일정이 있다면 무엇이든 편하게 말씀해 주세요."

    return IntentResult(
        intent="chat_only",
        ai_response=ai_response,
    )
