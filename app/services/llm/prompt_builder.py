from __future__ import annotations

import os
import random
import re

from app.config import get_now


def load_skill_instructions(gtd_path: str | None) -> str:
    """
    연결된 GTD 저장소(life_log) 내의 skills/gtd-assistant/SKILL.md 원문 전체를 읽어
    LLM(AGY 자율 에이전트)에 주입합니다 (ADR-032, ADR-066).
    """
    if not gtd_path or not os.path.exists(gtd_path):
        return ""

    skill_file = os.path.join(gtd_path, "skills", "gtd-assistant", "SKILL.md")
    if not os.path.exists(skill_file):
        skill_file = os.path.join(gtd_path, ".agents", "skills", "gtd-assistant", "SKILL.md")
    if not os.path.exists(skill_file):
        return ""

    try:
        with open(skill_file, "r", encoding="utf-8") as f:
            raw_skill = f.read().strip()
        if raw_skill:
            return f"\n[적용 스킬 명세: gtd-assistant (SKILL.md 원문 - ADR-066)]\n{raw_skill}\n"
    except OSError:
        pass

    return ""


def build_system_prompt(
    prompt: str,
    history: list[dict[str, str]] | None = None,
    gtd_path: str | None = None,
) -> str:
    """
    AGY 자율 에이전트에 전달할 시스템 프롬프트 및 대화 맥락을 조립합니다 (ADR-066).
    - 파이썬에서 인텐트 태그([INTENT: ...])를 강제하거나 분류하지 않습니다.
    - 에이전트는 작업 디렉토리(gtd_path)와 SKILL.md 규칙에 따라 직접 파일을 읽고 편집하며 자연스러운 한국어로 응답합니다.
    """
    now = get_now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    history_text = ""
    if history:
        recent = history[-5:]
        for h in recent:
            role_name = "사용자" if h.get("role") == "user" else "왓슨"
            content = str(h.get("content", "")).strip()
            if len(content) > 300:
                content = content[:300] + " ... (이하 생략)"
            history_text += f"{role_name}: {content}\n"

    full_prompt = (
        "너는 사용자의 24시간 개인 라이프로그 및 GTD AI 비서 왓슨(Watson)이다.\n"
        f"현재 한국 표준시(KST): {date_str} {time_str}\n"
        f"현재 작업 디렉토리(GTD 저장소): {gtd_path or '.'}\n\n"
        "핵심 행동 원칙 (ADR-064, ADR-066):\n"
        "1. 자율적 마크다운/GTD 관리:\n"
        "   - 사용자가 할 일 추가, 완료, 삭제, 상태 이동(예: inbox/next_actions ➔ someday_maybe.md / waiting_for.md), 또는 일기(`logs/daily/YYYY-MM-DD.md`) 기록을 요청하면, 아래 `gtd-assistant` 스킬 지침에 따라 직접 작업 디렉토리의 마크다운 파일을 읽고 편집해라.\n"
        "   - 사용자가 할 일이나 일기 조회/요약을 요청하면 실제 파일(`gtd/*.md`, `logs/daily/*.md`)을 읽고 정확하게 답변해라.\n"
        "2. Git 워크플로우 분리 (파이썬 전담):\n"
        "   - 네가 로컬 마크다운 파일을 수정하면 파이썬 백엔드가 `git status`로 변경을 자동 감지하고, 사용자가 `/commit`·`/push`를 입력하거나 매일 밤 23:30에 파이썬 스케줄러가 자동으로 일괄 커밋·푸시를 수행한다.\n"
        "   - 따라서 직접 `git commit`이나 `git push` 쉘 명령을 실행하지 마라.\n"
        "3. 응답 스타일:\n"
        "   - 어떠한 기계적 태그(`[INTENT: ...]`)도 출력하지 말고, 사용자에게 보여줄 친절하고 명확한 한국어 마크다운 답변만 출력해라.\n"
    )

    skill_instructions = load_skill_instructions(gtd_path)
    if skill_instructions:
        full_prompt += f"{skill_instructions}\n"

    if history_text:
        full_prompt += f"[최근 대화 맥락]\n{history_text}\n"
    full_prompt += f"[사용자 메시지]\n{prompt}\n\n왓슨의 답변:"
    return full_prompt


def get_smart_fallback(
    prompt: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """
    AGY CLI가 설치되지 않았거나 테스트(fast_mode) 환경일 때,
    인텐트 분류 정규식 없이 순수 대화 응답만 반환하는 경량 폴백입니다 (ADR-066).
    """
    prompt_clean = prompt.strip()

    # 브리핑 생성 프롬프트인 경우 빈 문자열을 반환하여 BriefingService의 기본 포맷터 사용 유도
    if any(b in prompt for b in ["Morning Briefing", "Evening Briefing", "Briefing]"]):
        return ""

    # 간단한 주사위/숫자 뽑기 유틸리티 응답
    match = re.search(r"(\d+)\s*부터\s*(\d+)", prompt_clean)
    if match:
        min_val, max_val = int(match.group(1)), int(match.group(2))
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        chosen = random.randint(min_val, max_val)
        return f"제가 **{min_val}부터 {max_val} 범위**에서 고른 숫자는 **{chosen}**입니다! 🎲"

    if any(w in prompt_clean for w in ["안녕", "반가워", "하이"]):
        return "안녕하세요! 👋 왓슨 AI 비서입니다. 오늘 하루는 어떠셨나요? 편하게 이야기 들려주세요!"

    return "네, 말씀 잘 들었습니다! 😊 오늘 있었던 일이나 정리할 GTD 할 일이 있다면 편하게 말씀해 주세요."
