from __future__ import annotations

import os
import random
import re

from app.config import get_now
from app.services.llm.category_extractor import (
    detect_category,
    extract_actionable_task,
)


def load_skill_instructions(gtd_path: str | None) -> str:
    """
    연결된 GTD 저장소(life_log) 내의 skills/gtd-assistant/SKILL.md 지침을 읽어
    프롬프트에 주입할 요약 행동 강령을 생성합니다 (ADR-032).
    """
    if not gtd_path or not os.path.exists(gtd_path):
        return ""

    skill_file = os.path.join(gtd_path, "skills", "gtd-assistant", "SKILL.md")
    if not os.path.exists(skill_file):
        skill_file = os.path.join(gtd_path, ".agents", "skills", "gtd-assistant", "SKILL.md")
    if not os.path.exists(skill_file):
        return ""

    return (
        "\n[적용 스킬: gtd-assistant (Getting Things Done)]\n"
        "- 상태와 시간의 엄격한 분리: 미완료 할 일은 오직 gtd/ 디렉토리 파일(inbox.md, next_actions.md 등)에서만 보관(SSOT).\n"
        "- 수술적 이동(Surgical Transfer): 할 일 완료 시 gtd/ 파일에서 해당 항목을 완전히 잘라내어(Cut) 제거하고, "
        "당일 데일리 로그(logs/daily/YYYY-MM-DD.md)의 '## ✅ 오늘 완료한 일 (Completed GTD Tasks)' 섹션으로 이동(Paste)함.\n"
        "- 데일리 로그에는 미완료 할 일을 남기거나 이월(Rollover)하지 않으며, 오직 완료된 성과만 기록함.\n"
    )


def build_system_prompt(
    prompt: str,
    history: list[dict[str, str]] | None = None,
    gtd_path: str | None = None,
) -> str:
    """
    AGY 엔진에 전달할 전체 시스템 프롬프트 및 대화 맥락, 그리고 ADR-061 의도 판별 프로토콜을 조립합니다.
    """
    history_text = ""
    if history:
        recent = history[-4:]
        for h in recent:
            role_name = "사용자" if h.get("role") == "user" else "왓슨"
            content = str(h.get("content", "")).strip()
            if len(content) > 250:
                content = content[:250] + " ... (이하 요약 생략)"
            history_text += f"{role_name}: {content}\n"

    full_prompt = (
        "너는 사용자의 24시간 개인 라이프로그 및 GTD AI 비서 왓슨(Watson)이다.\n"
        "친절하고 다정하며 센스 있게 한국어로 대화해라. 이전 대화 맥락이 있다면 자연스럽게 이어가라.\n\n"
        "중요 절대 규칙:\n"
        "- 코드 블록 실행이나 실제 Git 명령, 커밋, 푸시를 절대로 시뮬레이션하거나 대행한 척 거짓말하지 마라.\n"
        "- 가상의 브랜치나 저장소를 절대로 지어내지 마라. Git 작업은 백엔드가 직접 집행한다.\n"
        "- 사용자가 일기나 GTD 파일 기록 여부를 묻거나 일상 대화를 나눌 때 실제 파일에 기록되지 않았음에도 가상으로 기록했다고 거짓말하지 마라.\n"
        "- ADR-064 로컬 우선(Local-First) 정책: 평상시 일기/GTD 기록·완료·제거 시에는 로컬 마크다운 파일에 즉시 반영되며, 나중에 `/commit`·`/push` 명령 시 또는 매일 밤 23:30에 모아서 일괄 커밋·푸시된다.\n"
        "- 절대로 기계적인 앵무새 답변을 하지 마라. 구체적이고 도움이 되는 답변을 정성껏 제공해라.\n\n"

        "[의도 판별 및 행동 프로토콜 (Intent Protocol - ADR-061)]\n"
        "너는 사용자의 발화를 심층 분석하여, 액션이 필요한 경우 답변 첫 줄에 반드시 `[INTENT: ...]` 태그를 출력해야 한다.\n"
        "다음 줄부터는 사용자에게 전할 정성스럽고 따뜻한 한국어 답변을 작성해라.\n\n"
        "태그 출력 가이드:\n"
        "1. 일과/사건/생각/운동 등 기록 가치가 있는 일상을 공유했을 때 (사전 검토 제안):\n"
        "   - 운동 완료: `[INTENT: log_suggest category=\"Workout & Health\"]`\n"
        "   - 일상/가족/식사: `[INTENT: log_suggest category=\"Daily Notes & Diary\"]`\n"
        "   - 일상 중 할 일도 포함된 경우: `[INTENT: log_suggest category=\"Daily Notes & Diary\" gtd_task=\"<할일 내용>\"]`\n"
        "2. 명시적으로 오늘 일기나 GTD 파일 기록을 지시했을 때:\n"
        "   - 일기 기록: `[INTENT: log_explicit category=\"<카테고리>\"]`\n"
        "   - GTD 할일 등록: `[INTENT: log_explicit category=\"GTD Inbox\" gtd_task=\"<할일 내용>\"]`\n"
        "   - 둘 다 동시 기록: `[INTENT: log_dual category=\"Daily Notes & Diary\" gtd_task=\"<할일 내용>\"]`\n"
        "3. GTD 할 일을 완료했다고 하거나 완료 처리를 요청할 때:\n"
        "   `[INTENT: task_complete target=\"<완료한 작업명>\"]`\n"
        "4. GTD 할 일을 삭제/제거해달라고 요청할 때:\n"
        "   `[INTENT: gtd_remove target=\"<삭제할 작업명>\"]`\n"
        "5. 일일 로그 또는 GTD 파일 원본 조회를 요청할 때:\n"
        "   - 오늘 일기 확인: `[INTENT: daily_log_inspect]`\n"
        "   - GTD 인박스/할일 확인: `[INTENT: gtd_inspect]`\n"
        "   - 둘 다 확인: `[INTENT: gtd_and_log_inspect]`\n"
        "   - 마감일/D-day 확인: `[INTENT: dday_inspect]`\n"
        "6. 오늘 할 일/일정 브리핑을 요청할 때:\n"
        "   - 아침 브리핑: `[INTENT: task_briefing_morning]`\n"
        "   - 저녁 브리핑/회고: `[INTENT: task_briefing_evening]`\n"
        "   - 일반 브리핑: `[INTENT: task_briefing]`\n"
        "   - 브리핑 스케줄: `[INTENT: briefing_schedule_inspect]`\n"
        "7. 출근길 날씨, 미세먼지, 버스 정보를 물어볼 때:\n"
        "   - 버스: `[INTENT: commute_inspect mode=\"bus\"]`\n"
        "   - 날씨/미세먼지: `[INTENT: commute_inspect mode=\"weather\"]`\n"
        "   - 출근길 전체: `[INTENT: commute_inspect mode=\"status\"]`\n"
        "8. 저장소 동기화/푸시/커밋을 요청할 때:\n"
        "   - 푸시: `[INTENT: repo_push]`\n"
        "   - 동기화/최신화: `[INTENT: repo_sync]`\n"
        "   - 커밋: `[INTENT: repo_commit]`\n"
        "9. 오늘 일기/로그 기록 여부를 물어보거나 점검할 때:\n"
        "   `[INTENT: log_status_inspect]`\n"
        "10. 과거 기록 검색이나 주간 결산을 요청할 때:\n"
        "   - 과거 검색: `[INTENT: search_query query=\"<검색어>\"]`\n"
        "   - 주간 결산: `[INTENT: weekly_review]`\n"
        "11. 잔디(기여도)나 일기 편집을 요청할 때:\n"
        "   - 잔디: `[INTENT: lifelog_heatmap]`\n"
        "   - 일기 편집: `[INTENT: lifelog_edit]`\n"
        "12. 일반 대화, 질의응답, 인사, 잡담 등 그 외 모든 경우:\n"
        "   태그 없이 일반 답변만 출력하거나 `[INTENT: chat_only]`를 출력해라.\n\n"
    )

    skill_instructions = load_skill_instructions(gtd_path)
    if skill_instructions:
        full_prompt += f"{skill_instructions}\n"

    if history_text:
        full_prompt += f"[이전 대화 내역]\n{history_text}\n"
    full_prompt += f"[사용자 입력]\n{prompt}\n\n왓슨 비서로서 답변:"
    return full_prompt


def get_smart_fallback(
    prompt: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """
    AGY 미구동 또는 테스트 모드 시 ADR-061 인텐트 프로토콜을 준수하는
    시맨틱 폴백 응답을 생성합니다 (ADR-008, ADR-010, ADR-048, ADR-061).
    """
    prompt_clean = prompt.strip()
    prompt_lower = prompt_clean.lower()
    time_str = get_now().strftime("%H:%M")
    date_str = get_now().strftime("%Y-%m-%d")

    # 브리핑 생성 프롬프트인 경우 잡담 폴백을 우회하고 빈 문자열 반환 (결정론적 룰 기반 브리핑으로 폴백 유도)
    if any(b in prompt for b in ["Morning Briefing", "Evening Briefing", "Briefing]"]):
        return ""

    # 1. 부정 / 불필요 / 취소 가드레일 (ADR-036)
    negative_feedback_patterns = [
        r"필요\s*(?:가\s*)?없",
        r"안\s*(?:사도|해도|가도|먹어도|시켜도|봐도|있어도)\s*(?:돼|됨|된다|괜찮)",
        r"(?:살|할|갈|먹을|시킬)\s*필요\s*없",
        r"(?:선물\s*받아|선물받아|이미\s*있|벌써\s*있)",
        r"(?:취소|환불|철회)",
    ]
    if any(re.search(pat, prompt_clean, re.IGNORECASE) for pat in negative_feedback_patterns):
        return "[INTENT: chat_only]\n네, 말씀해 주신 변경 사항 잘 이해했습니다! 추가로 정리할 내용이 있다면 편하게 말씀해 주세요. 😊"

    # 2. 메타 피드백 / 항의 발화 가드레일 (ADR-031)
    meta_protest_patterns = [
        r"^(?:아니\s*)?(?:이미|벌써)?\s*.*?(?:있다면서|있잖아|했다면서|했잖아|말했잖아|그게\s*아니|왜\s*또|왜\s*새로|왜\s*등록|말한\s*건데|말한거야|말한건가|무슨\s*소리|이게\s*뭐야|그게\s*아닌데|누가\s*등록|등록하라는게\s*아니)",
        r"^(?:아니|그게\s*아니라)\s*.*?(?:완료|끝|해결|삭제|제거).*?(?:말한|한\s*건데|거야|잖아)",
        r".*?(?:있다면서|했다면서|말했잖아|그게\s*아니라|말한\s*건데|말한거야)[\?\!\.\s]*$",
    ]
    if any(re.search(pat, prompt_clean, re.IGNORECASE) for pat in meta_protest_patterns):
        target = ""
        m_task = re.search(r"([가-힣a-zA-Z0-9\s]{2,25}?)\s*(?:완료했다고|완료한|끝났다고|해결했다고|완료)", prompt_clean)
        if m_task and len(m_task.group(1).strip()) >= 2:
            t_cand = m_task.group(1).strip()
            if not any(k in t_cand for k in ["아니", "인박스", "이미", "그래서", "말한"]):
                target = t_cand
        if not target and history:
            for h in reversed(history):
                if h.get("role") == "user":
                    cleaned_prev = re.sub(r"(완료\s*gtd에\s*기록해|완료했어|완료|끝났어|gtd에\s*기록해|기록해)[\.\!\?\s]*$", "", h.get("content", "")).strip()
                    cleaned_prev = re.sub(r"[은는이가을를도]$", "", cleaned_prev).strip()
                    if len(cleaned_prev) >= 2 and not any(k in cleaned_prev for k in ["아니", "인박스", "이미", "/", "briefing", "schedule"]):
                        target = cleaned_prev
                        break
        return f'[INTENT: task_complete target="{target}"]\n오해하여 잘못 안내해 드려 죄송합니다! 🙇‍♂️ 기존 GTD 항목을 찾아 즉시 완료 처리했습니다.'

    # 3. 복합 기록 (데일리 로그 + GTD 인박스 동시 기록 - ADR-014)
    dual_pattern = r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:데일리\s*)?(?:라이프\s*)?(?:로그\s*와|로그\s*랑|일기\s*와|일기\s*랑|다이어리\s*와|다이어리\s*랑)\s*(?:gtd\s*에?|할일\s*(?:에|에?도)?|인박스\s*에?|수집함\s*에?)\s*(?:둘\s*다|모두|함께|동시에)?\s*(?:에|로|을|를|도)?\s*(?:기록해줘|적어줘|남겨줘|넣어줘|추가해줘|올려줘|등록해줘|기록해|메모해줘)[\.\!\?\s]*$"
    dual_reverse_pattern = r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:gtd\s*와|gtd\s*랑|할일\s*과|할일\s*이랑|인박스\s*와|인박스\s*랑)\s*(?:데일리\s*)?(?:라이프\s*)?(?:로그\s*에?|일기\s*에?|다이어리\s*에?)\s*(?:둘\s*다|모두|함께|동시에)?\s*(?:에|로|을|를|도)?\s*(?:기록해줘|적어줘|남겨줘|넣어줘|추가해줘|올려줘|등록해줘|기록해|메모해줘)[\.\!\?\s]*$"
    dual_m = re.search(dual_pattern, prompt_clean, re.IGNORECASE) or re.search(dual_reverse_pattern, prompt_clean, re.IGNORECASE)
    if dual_m:
        cleaned_story = prompt_clean[:dual_m.start()].strip()
        cleaned_story = re.sub(r"^(응|어|네|예|그래|좋아|좋아요)\s*", "", cleaned_story).strip()
        gtd_task = extract_actionable_task(cleaned_story)
        cat = "Daily Notes & Diary"
        return (
            f'[INTENT: log_dual category="{cat}" gtd_task="{gtd_task}" content="{cleaned_story}"]\n'
            f"소중한 일상 이야기는 오늘 자 **[{cat}]**에 기록하고, "
            f"실행 태스크(`- [ ] {gtd_task}`)는 **GTD 수집함(inbox.md)**에 등록했습니다! 📝📥✨"
        )

    # 4. 문두 기록 지시어 (ADR-028)
    front_pattern = (
        r"^(?:아니\s*)?(?:어제|오늘|오늘자|데일리)?\s*(?:자\s*)?(?:라이프\s*)?"
        r"(?:로그|일기|다이어리|gtd|인박스|수집함|할일)?\s*(?:에|로)?\s*"
        r"(?:이\s*내용|이\s*이야기|이\s*글|이거|내용)?\s*(?:을|를|도)?\s*"
        r"(?:기록해줘|적어줘|남겨줘|넣어줘|넣어달라구|넣어달라|추가해줘|올려줘|등록해줘|반영해줘|메모해줘)[:\s\n]+(.+)"
    )
    front_m = re.search(front_pattern, prompt_clean, re.DOTALL | re.IGNORECASE)
    if front_m:
        body = front_m.group(1).strip()
        prefix = prompt_clean[:front_m.start(1)].lower()
        is_gtd = any(k in prefix for k in ["gtd", "인박스", "inbox", "수집함", "할일"])
        if is_gtd:
            task = extract_actionable_task(body)
            return f'[INTENT: log_explicit category="GTD Inbox" gtd_task="{task}" content="{body}"]\n요청하신 태스크(`- [ ] {task}`)를 **GTD 수집함(inbox.md)**에 등록하고 GitHub에 커밋했습니다! 📥🚀'
        else:
            cat = detect_category(body)
            return f'[INTENT: log_explicit category="{cat}" content="{body}"]\n보내주신 소중한 일과와 감정을 라이프로그 **[{cat}]**에 즉시 기록하고 GitHub에 커밋했습니다! 📝✨'

    # 5. 맥락 참조 기록 지시어 (ADR-010, ADR-012)
    record_action_pattern = r"(?:기록|적어|남겨|올려|저장|써|메모|넣어|추가|등록|반영|업데이트)\s*(?:해줘|줘|주세요|부탁|해|달라|달라구|하기|하자)"
    context_ref_pattern = r"(?:아까|방금|이전|앞서|지난|위|위의|위ㅡ|이|그)\s*(?:말한|한|이야기|대화|내용|글|것|거)"
    has_ref = bool(re.search(context_ref_pattern, prompt_clean)) or (
        any(k in prompt_clean for k in ["아까", "방금", "이전", "앞서"]) and any(k in prompt_clean for k in ["말", "이야기", "내용"])
    )
    has_rec = bool(re.search(record_action_pattern, prompt_clean))
    stripped_directive = prompt_clean
    stripped_directive = re.sub(r"^(응|어|네|예|그래|좋아|좋아요|오케이|ok|yes)\s*", "", stripped_directive, flags=re.IGNORECASE)
    stripped_directive = re.sub(r"(오늘|오늘자|오늘의|내일|어제)?\s*(라이프\s*로그|로그|일기|다이어리|수집함|인박스)?\s*(?:에|로|을|를)?\s*", "", stripped_directive)
    stripped_directive = re.sub(r"(기록|적어|남겨|올려|저장|써|메모|넣어|추가|등록|반영|업데이트)\s*(해줘|줘|주세요|부탁해|해|달라|달라구)?\s*", "", stripped_directive)
    stripped_directive = re.sub(r"(이|그)?\s*(내용|이야기|글|것|거|말)?\s*(?:도|은|는|이|가)?\s*", "", stripped_directive)
    is_pure_dir = has_rec and len(stripped_directive.strip()) <= 2
    if (has_ref or is_pure_dir) and has_rec and history:
        prev_user = next(
            (
                h["content"].strip()
                for h in reversed(history)
                if h.get("role") == "user"
                and len(h.get("content", "").strip()) > 8
                and not any(h.get("content", "").strip().startswith(cp) for cp in ["기록해", "푸시", "확인", "동기화", "pull", "push", "sync", "/", "응"])
            ),
            None,
        )
        if prev_user:
            is_gtd = any(k in prompt_lower for k in ["gtd", "인박스", "inbox", "수집함", "할일"])
            if is_gtd:
                task = extract_actionable_task(prev_user)
                return f'[INTENT: log_explicit category="GTD Inbox" gtd_task="{task}" content="{prev_user}"]\n이전 이야기에서 추출한 태스크(`- [ ] {task}`)를 **GTD 수집함(inbox.md)**에 등록하고 GitHub에 커밋했습니다! 📥🚀'
            cat = detect_category(f"{prompt_clean} {prev_user}")
            snippet = prev_user[:25] + "..." if len(prev_user) > 25 else prev_user
            return f'[INTENT: log_explicit category="{cat}" content="{prev_user}"]\n나누어 주신 소중한 이야기(\'{snippet}\')를 오늘 자 라이프로그 **[{cat}]**에 기록하고 GitHub에 커밋했습니다! 🕯️📝'

    # 6. 단일 후미 기록 명령 (ADR-014, ADR-059)
    single_end_pattern = (
        r"[\s,.]*(?:이\s*내용|이\s*이야기|이\s*글|이거|이것도)?\s*(?:오늘\s*)?(?:자\s*)?(?:데일리\s*)?(?:라이프\s*)?"
        r"(?:로그|일기|다이어리|gtd|인박스|수집함|할일)?\s*(?:에|로|을|를|도)?\s*"
        r"(?:기록해줘|기록해|기록|적어줘|적어|남겨줘|남겨|넣어줘|넣어|추가해줘|추가해|추가|올려줘|올려|등록해줘|등록해|등록|메모해줘|메모해|메모)"
        r"[\.\!\?\s]*$"
    )
    single_end_m = re.search(single_end_pattern, prompt_clean, re.IGNORECASE)
    if single_end_m and len(prompt_clean[:single_end_m.start()].strip()) > 3:
        cleaned_body = prompt_clean[:single_end_m.start()].strip()
        cleaned_body = re.sub(r"^(응|어|네|예|그래|좋아|좋아요)\s*", "", cleaned_body).strip()
        matched_suffix = single_end_m.group(0).lower()
        if any(k in matched_suffix for k in ["gtd", "인박스", "inbox", "수집함", "할일"]):
            if any(w in cleaned_body for w in ["완료", "끝", "해결", "체크"]):
                pure_task = re.sub(r"(완료|끝|해결|체크)[\.\!\?\s]*$", "", cleaned_body).strip()
                pure_task = re.sub(r"[은는이가을를도]$", "", pure_task).strip()
                return f'[INTENT: task_complete target="{pure_task}"]\n태스크를 완료 처리했습니다.'
            task = extract_actionable_task(cleaned_body)
            return f'[INTENT: log_explicit category="GTD Inbox" gtd_task="{task}"]\n요청하신 태스크(`- [ ] {task}`)를 **GTD 수집함(inbox.md)**에 등록하고 GitHub에 커밋했습니다! 📥🚀'
        else:
            cat = detect_category(cleaned_body)
            return f'[INTENT: log_explicit category="{cat}" content="{cleaned_body}"]\n보내주신 소중한 일과와 감정을 오늘 자 라이프로그 **[{cat}]**에 즉시 기록하고 GitHub에 커밋했습니다! 📝✨'

    # 7. 구어체 태스크 완료 (ADR-027, ADR-031)
    complete_gtd_match = re.search(
        r"^(.*?)(?:은|는|이|가|도)?\s*(?:완료|해결|끝|체크)\s*(?:처리)?\s*(?:도|는|은)?\s*"
        r"(?:오늘\s*)?(?:자\s*)?(?:gtd|인박스|inbox|수집함|할일|next\s*actions)?\s*(?:에|로|도)?\s*"
        r"(?:기록해줘|기록해|적어줘|남겨줘|반영해줘|반영해|체크해줘|체크해|체크)[\.\!\?\s]*$",
        prompt_clean,
        re.IGNORECASE,
    )
    colloquial_match = re.search(
        r"^(.*?)(?:은|는|이|가|도)?\s*"
        r"(?:완료했어|완료함|완료|끝났어|끝냈어|끝냄|다했어|다했다|해결했어|해결함|해결|마쳤어|마침|해치웠어|체크해줘|체크함|체크)[\.\!\?\s]*$",
        prompt_clean,
        re.IGNORECASE,
    )
    raw_target = ""
    if complete_gtd_match:
        raw_target = complete_gtd_match.group(1).strip()
    elif colloquial_match and len(colloquial_match.group(1).strip()) <= 45:
        raw_target = colloquial_match.group(1).strip()

    if raw_target:
        workout_keywords = ["헬스장", "스쿼트", "푸시업", "벤치프레스", "데드리프트", "런닝", "달리기", "러닝", "산책", "유산소", "웨이트", "운동"]
        is_workout = any(wk in raw_target for wk in workout_keywords)
        if not is_workout and not any(k in raw_target for k in ["아니", "인박스", "이미"]):
            raw_target = re.sub(r"^(응|어|네|예|그래|좋아|오늘|오늘자|자|gtd|인박스|할일|태스크)\s*", "", raw_target).strip()
            raw_target = re.sub(r"[은는이가을를도]$", "", raw_target).strip()
            return f'[INTENT: task_complete target="{raw_target}"]\n태스크를 완료 처리했습니다.'

    # 8. GTD 태스크 제거 (ADR-020)
    remove_triggers = ["제거", "삭제", "빼줘", "빼", "지워", "지워줘", "제외", "제외해"]
    if any(rt in prompt_clean for rt in remove_triggers) and any(k in prompt_clean for k in ["는", "도", "은", "를", "을", "에서", "할일", "태스크", "인박스", "tiara", "아젠다", "보고", "지원", "시간", "gtd", "케어"]):
        return f'[INTENT: gtd_remove target="{prompt_clean}"]\n요청하신 GTD 항목을 제거했습니다.'

    # 9. 푸시 / 동기화 / 커밋 (ADR-011, ADR-009, ADR-020)
    if any(w in prompt_clean.lower() for w in ["푸시", "push"]) and not any(w in prompt_clean.lower() for w in ["푸시업", "pushup", "push-up", "push up"]):
        mode = "query" if any(q in prompt_clean for q in ["어디", "주소", "확인", "맞아"]) else "push"
        return f'[INTENT: repo_push mode="{mode}"]\n저장소 푸시 요청을 실행합니다.'
    if any(st in prompt_clean.lower() for st in ["최신화", "동기화", "pull", "sync"]):
        if any(brt in prompt_clean.lower() for brt in ["알려", "정리", "보여", "브리핑", "요약", "보고", "체크"]):
            return "[INTENT: repo_sync_and_briefing]\n최신 GTD 저장소 동기화 후 브리핑을 준비합니다."
        return "[INTENT: repo_sync]\n저장소를 동기화합니다."
    if any(k in prompt_clean for k in ["커밋해", "커밋해줘", "커밋하자", "깃 커밋", "git commit"]):
        return "[INTENT: repo_commit]\n저장소 커밋을 실행합니다."

    # 10. 기록 상태 점검 (ADR-028)
    status_patterns = [
        r"(?:오늘|오늘자|데일리)?\s*(?:라이프\s*)?(?:로그|일기|다이어리|기록|파일)?\s*(?:에|로)?\s*(?:기록했어|적었어|남겼어|썼어|올렸어|들어갔어|반영됐어|반영된거야|기록된거야|기록된\s*거\s*맞아|기록된거\s*맞아|기록\s*됐어|기록\s*됐니|기록됐니|적혔어|적힌거야|저장됐어|저장했어|기록된건가)[\?\.\!\s]*$",
        r"^(?:오늘|오늘자|오늘의|데일리)?\s*(?:라이프\s*)?(?:기록|일기|로그)\s*(?:확인|점검|체크|상태|확인해줘)[\?\.\!\s]*$",
        r"^(?:오늘|오늘자|오늘의|데일리)?\s*(?:라이프\s*)?(?:기록|일기|로그)\s*(?:됐어|된거야|된\s*건가|했어|한거야)[\?\.\!\s]*$",
        r"^(?:오늘\s*)?기록\s*했어[\?\.\!\s]*$",
        r"^(?:오늘\s*)?기록\s*됐어[\?\.\!\s]*$",
        r"^(?:오늘\s*)?일기\s*확인해줘[\?\.\!\s]*$",
        r"^(?:오늘\s*)?로그\s*확인해줘[\?\.\!\s]*$",
    ]
    if any(re.search(pat, prompt_lower, re.IGNORECASE) for pat in status_patterns):
        return "[INTENT: log_status_inspect]\n일일 로그 기록 상태를 확인합니다."

    # 11. 직접 조회 (일일 로그, GTD 수집함, 마감일) (ADR-022, ADR-042, ADR-060)
    if any(re.search(pat, prompt_lower, re.IGNORECASE) for pat in [
        r"^(?:오늘|오늘자|오늘의|데일리)\s*(?:라이프\s*)?(?:로그|일기|기록)\s*(?:보여줘|보여|읽어줘|읽어|확인|열어줘|열어|출력|조회|알려줘|어떻게\s*돼|내용)?[\.\!\?\s]*$",
    ]):
        return "[INTENT: daily_log_inspect]\n오늘 일일 로그를 조회합니다."

    if any(re.search(pat, prompt_lower, re.IGNORECASE) for pat in [
        r"^(?:gtd|inbox(?:\.md)?|인박스|수집함|next_actions(?:\.md)?|다음\s*행동)(?:\s+(?:gtd|inbox(?:\.md)?|인박스|수집함|next_actions(?:\.md)?|다음\s*행동))*\s*(?:파일|문서|원본|마크다운|내용|목록|리스트)?\s*(?:보여줘|보여|읽어줘|읽어|확인해줘|확인|열어줘|열어|출력|조회|체크)?[\.\!\?\s]*$",
    ]):
        return "[INTENT: gtd_inspect]\nGTD 목록을 조회합니다."

    if any(k in prompt_lower for k in ["마감일", "마감 임박", "d-day", "dday", "디데이", "기한"]):
        return "[INTENT: dday_inspect]\n마감일 현황을 조회합니다."

    # 12. 주간 결산 및 회고 (ADR-043) - 저녁 브리핑보다 먼저 검사하여 '이번 주 회고' 오탐 방지
    if any(k in prompt_lower for k in ["주간 결산", "주간 회고", "주간 리포트", "이번 주 회고", "이번주 회고", "한 주 돌아보기", "이번 주", "이번주"]) and any(v in prompt_lower for v in ["결산", "회고", "리포트", "정리", "보고", "알려", "보여"]):
        return "[INTENT: weekly_review]\n주간 결산 리포트를 준비합니다."

    # 13. 브리핑 및 스케줄 (ADR-008, ADR-024, ADR-025)
    if any(k in prompt_lower for k in ["스케줄", "스케쥴", "몇 시에 스케줄링", "몇시에 스케줄링"]):
        return "[INTENT: briefing_schedule_inspect]\n브리핑 스케줄을 확인합니다."
    if any(m in prompt_lower for m in ["아침", "모닝", "출근"]) and any(b in prompt_lower for b in ["브리핑", "일정", "할일", "시작", "정리"]):
        return "[INTENT: task_briefing_morning]\n오늘 아침 브리핑을 준비합니다."
    if any(e in prompt_lower for e in ["저녁", "이브닝", "퇴근", "회고", "정산", "마무리"]) and any(b in prompt_lower for b in ["브리핑", "일정", "할일", "회고", "정리", "정산", "마무리"]):
        return "[INTENT: task_briefing_evening]\n오늘 저녁 일과 회고 브리핑을 준비합니다."
    if any(b in prompt_lower for b in ["브리핑", "해야할 일", "할 일", "할일", "투두"]):
        return "[INTENT: task_briefing]\n오늘의 브리핑을 준비합니다."

    # 14. 출근길 / 날씨 / 버스 / 동네 (ADR-030, ADR-033, ADR-034)
    if any(k in prompt_lower for k in ["출근 버스", "버스 언제", "버스 도착", "버스 정보", "버스 시간", "몇 분 뒤 와", "몇분 뒤 와"]):
        return '[INTENT: commute_inspect mode="bus"]\n실시간 버스 정보를 조회합니다.'
    if any(k in prompt_lower for k in ["날씨 브리핑", "날씨 정보", "미세먼지 정보", "미세먼지", "대기질"]):
        return '[INTENT: commute_inspect mode="weather"]\n실시간 날씨 및 대기질 정보를 조회합니다.'
    if any(k in prompt_lower for k in ["동네", "지역", "거주지", "우리동네", "우리 동네"]):
        if any(q in prompt_lower for q in ["어디", "확인", "현재"]) or not any(v in prompt_lower for v in ["설정", "변경", "바꿔", "등록"]):
            return "[INTENT: location_inspect]\n현재 설정된 거주지 동네를 확인합니다."
        return f'[INTENT: location_set query="{prompt_clean}"]\n거주지 동네를 설정합니다.'

    # 15. 검색 / 편집 / 잔디 (ADR-043, ADR-045)
    if any(k in prompt_lower for k in ["찾아줘", "찾아봐", "검색해줘", "검색"]):
        kw = re.sub(r"^(?:과거|이전|예전|지난|라이프로그|일기|로그|gtd)\s*(?:에서|의)?\s*", "", prompt_clean).strip()
        kw = re.sub(r"(?:검색해줘|검색해|검색|찾아줘|찾아봐|찾아)[\.\!\?\s]*$", "", kw).strip()
        return f'[INTENT: search_query query="{kw}"]\n과거 기록을 검색합니다.'
    if any(k in prompt_lower for k in ["일기 편집", "로그 수정", "로그 편집", "일기 수정"]):
        return "[INTENT: lifelog_edit]\n일일 로그 편집기를 엽니다."
    if any(k in prompt_lower for k in ["잔디", "히트맵", "기여도"]):
        return "[INTENT: lifelog_heatmap]\n라이프로그 잔디를 확인합니다."
        return "[INTENT: lifelog_edit]\n일일 로그 편집기를 엽니다."
    if any(k in prompt_lower for k in ["잔디", "히트맵", "기여도"]):
        return "[INTENT: lifelog_heatmap]\n라이프로그 잔디를 확인합니다."

    # 15. 운동 서사 발화 (Workout & Health - ADR-004, ADR-029)
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
    if any(re.search(t, prompt_clean, re.IGNORECASE) for t in workout_terms) or "푸시업" in prompt_clean:
        cat = "Workout & Health"
        return (
            f'[INTENT: log_suggest category="{cat}" content="{prompt_clean}"]\n'
            f"건강을 챙기시는 모습이 정말 멋지십니다! 🏋️ 오늘 운동 기록({cat})에 아래 초안대로 **기록해 둘까요?** 📝\n\n"
            f"---\n"
            f"### 📝 라이프로그 초안 (`logs/daily/{date_str}.md` [{cat}])\n"
            f"- [{time_str}] {prompt_clean}\n"
            f"---\n"
            f"👉 **'응'** 또는 아래 **[✅ 응, 기록해줘]** 버튼을 눌러주시면 즉시 GitHub에 커밋·푸시합니다! ✨"
        )

    # 16. 일상 / 가족 / 감정 서사 발화 (Daily Notes & Diary - ADR-029)
    narrative_actions = ["끓였어", "차렸어", "먹었어", "다녀왔어", "갔다왔어", "퇴근하고", "수술하고", "진료받고", "치료받고", "간호했어"]
    life_subjects = ["아내", "와이프", "남편", "가족", "아이", "아기", "부모님", "미역국", "소파술", "병원"]
    if any(act in prompt_clean for act in narrative_actions) and any(sub in prompt_clean for sub in life_subjects):
        cat = "Daily Notes & Diary"
        return (
            f'[INTENT: log_suggest category="{cat}" content="{prompt_clean}"]\n'
            f"소중한 일상과 마음을 나누어 주셔서 감사합니다. 😊\n\n"
            f"말씀해주신 소중한 일과를 아래와 같이 정리했습니다. 이대로 **기록해 둘까요?** 📝\n\n"
            f"---\n"
            f"### 📝 라이프로그 초안 (`logs/daily/{date_str}.md` [{cat}])\n"
            f"- [{time_str}] {prompt_clean}\n"
            f"---\n"
            f"👉 **'응'** 또는 아래 **[✅ 응, 기록해줘]** 버튼을 눌러주시면 즉시 GitHub에 커밋·푸시합니다! ✨"
        )

    # 17. 빠른 응답 패턴 (숫자 뽑기)
    if re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean) or ("숫자" in prompt_clean and "골라" in prompt_clean):
        match = re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean)
        if match:
            min_val, max_val = int(match.group(1)), int(match.group(2))
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            chosen = random.randint(min_val, max_val)
            return f"[INTENT: chat_only]\n제가 **{min_val}부터 {max_val} 범위**에서 고른 숫자는 **{chosen}**입니다! 🎲 마음에 드시나요?"
        else:
            chosen = random.randint(1, 30)
            return f"[INTENT: chat_only]\n제가 고른 숫자는 **{chosen}**입니다! 🎲 마음에 드시나요?"

    # 18. 기본 일반 대화
    if any(w in prompt_clean for w in ["누구", "왓슨"]):
        return (
            "[INTENT: chat_only]\n"
            "저는 24시간 사용자의 삶의 기록(Life Log)과 GTD를 관리하는 **Watson AI 비서**입니다. 🤖\n"
            "일상 대화부터 오늘 해야 할 일 브리핑, 소중한 일과와 생각을 GitHub 마크다운으로 깔끔하게 기록해 드립니다!"
        )
    if any(w in prompt_clean for w in ["안녕", "반가워", "하이"]):
        return "[INTENT: chat_only]\n안녕하세요! 👋 왓슨 AI 비서입니다. 오늘 하루는 어떠셨나요? 편하게 이야기 들려주세요!"

    if history and len(history) > 0:
        return (
            "[INTENT: chat_only]\n"
            "말씀해 주신 깊은 마음과 생각 잘 헤아리고 있습니다. 곁에서 언제나 든든한 버팀목이 되어 드릴 테니, "
            "필요하신 점이나 덧붙이고 싶은 일과가 있다면 편하게 이어서 말씀해 주세요. 🕯️"
        )

    return "[INTENT: chat_only]\n네, 사용자님 말씀 잘 듣고 있습니다! 😊 오늘 하루 있었던 일과나 나누고 싶은 생각, 혹은 정리할 일정이 있다면 무엇이든 편하게 말씀해 주세요."
