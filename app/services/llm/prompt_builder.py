from __future__ import annotations

import os


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
    """AGY 엔진에 전달할 전체 시스템 프롬프트 및 대화 맥락을 조립합니다 (ADR-010, ADR-011, ADR-028)."""
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
        "친절하고 다정하며 센스 있게 한국어로 대화해라. 이전 대화 맥락이 있다면 자연스럽게 이어가라.\n"
        "중요 절대 규칙:\n"
        "- 코드 블록 실행이나 실제 Git 명령, 커밋, 푸시를 절대로 시뮬레이션하거나 대행한 척 거짓말하지 마라.\n"
        "- 가상의 브랜치나 저장소(origin/private-lifelog 등)를 절대로 지어내지 마라. Git 작업은 백엔드가 직접 집행한다.\n"
        "- 저장소 푸시/커밋 상태에 대한 질문에는 '백엔드에서 실제 Git 상태를 점검하시려면 /status, /sync, /push 명령어를 사용해 달라'고 정직하게 안내하라.\n"
        "- 사용자가 일기나 GTD 파일 기록 여부('기록했어?', '오늘 일기 적었어?' 등)를 묻거나 일상 대화를 나눌 때, "
        "실제 파일에 기록되지 않았음에도 가상으로 '정리해 두었습니다', '기록했습니다'라고 시뮬레이션하거나 거짓말하지 마라. "
        "물리적 마크다운 파일 기록은 백엔드가 직접 집행하므로, '실제 파일 기록 여부는 /today 또는 /gtd로 확인하실 수 있으며, "
        "방금 나누어주신 일과를 실제 파일에 기록하시려면 \"기록해줘\"라고 말씀해 주세요'라고 정직하게 안내하라.\n"
        "- 절대로 '이야기 잘 들었습니다' 같은 기계적이고 판에 박힌 앵무새 답변을 하지 마라. "
        "사용자의 질문이나 대화에 귀기울이고 구체적이고 도움이 되는 답변을 정성껏 제공해라.\n\n"
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
    """AGY 미구동 또는 오류 시 결정론적 로컬 스마트 폴백 응답을 생성합니다 (ADR-008, ADR-010)."""
    # 브리핑 생성 프롬프트인 경우 잡담 폴백을 우회하고 빈 문자열 반환 (결정론적 룰 기반 브리핑으로 폴백 유도)
    if any(b in prompt for b in ["Morning Briefing", "Evening Briefing", "Briefing]"]):
        return ""

    if any(w in prompt for w in ["누구", "왓슨"]):
        return (
            "저는 24시간 사용자의 삶의 기록(Life Log)과 GTD를 관리하는 **Watson AI 비서**입니다. 🤖\n"
            "일상 대화부터 오늘 해야 할 일 브리핑, 소중한 일과와 생각을 GitHub 마크다운으로 깔끔하게 기록해 드립니다!"
        )
    if any(w in prompt for w in ["안녕", "반가워", "하이"]):
        return "안녕하세요! 👋 왓슨 AI 비서입니다. 오늘 하루는 어떠셨나요? 편하게 이야기 들려주세요!"
    if any(w in prompt for w in ["날씨", "시간"]):
        return "오늘도 활기차고 좋은 하루 보내시길 바랍니다! 궁금한 점이 있으시거나 나누고 싶은 이야기가 있다면 언제든 말씀해 주세요. ☀️"

    if history and len(history) > 0:
        if any(k in prompt for k in ["푸시", "커밋", "동기화", "확인", "깃", "오류", "에러", "실행", "명령"]):
            return (
                "요청하신 작업 상태를 확인하고 있습니다. `/status`, `/sync`, `/push` 명령어로 저장소 상태를 직접 점검 및 실행하실 수 있습니다. 🤖"
            )
        return (
            "말씀해 주신 깊은 마음과 생각 잘 헤아리고 있습니다. 곁에서 언제나 든든한 버팀목이 되어 드릴 테니, "
            "필요하신 점이나 덧붙이고 싶은 일과가 있다면 편하게 이어서 말씀해 주세요. 🕯️"
        )

    return "네, 사용자님 말씀 잘 듣고 있습니다! 😊 오늘 하루 있었던 일과나 나누고 싶은 생각, 혹은 정리할 일정이 있다면 무엇이든 편하게 말씀해 주세요."
