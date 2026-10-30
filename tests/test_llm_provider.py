import os
import tempfile

from app.services.llm.prompt_builder import build_system_prompt, load_skill_instructions
from app.services.llm_provider import LLMProvider


def test_llm_provider_natural_language_delegated_without_intent_classification():
    """ADR-066: 슬래시(/)가 아닌 모든 자연어 입력은 파이썬이 인텐트를 분류하거나 가로채지 않고 100% LLM 응답(chat_only)으로 위임됨을 검증."""
    provider = LLMProvider(fast_mode=True)

    natural_inputs = [
        "안녕? 오늘 날씨 어때?",
        "오늘 퇴근하고 헬스장에서 스쿼트 100kg 성공했어!",
        "은퇴 계획 일정을 someday로 이동시켜줘",
        "트래블월렛 고객확인 gtd에 추가",
        "오늘 gtd 할일 확인해줘",
        "민방위 사이버교육은 완료했어.",
        "휴지는 선물받아서 구매할 필요가 없어.",
    ]
    for msg in natural_inputs:
        res = provider.analyze_and_respond(msg)
        assert res.intent == "chat_only", f"Natural language '{msg}' must not be classified by Python, got {res.intent}"
        assert len(res.ai_response.strip()) > 0


def test_llm_provider_slash_command_routing():
    """ADR-061 & ADR-066: 오직 명시적 슬래시(/) 명령어만 파이썬 결정론적 워크플로우로 즉시 라우팅됨을 검증."""
    provider = LLMProvider(fast_mode=True)

    assert provider.analyze_and_respond("/today").intent == "daily_log_inspect"
    assert provider.analyze_and_respond("/gtd").intent == "gtd_inspect"
    assert provider.analyze_and_respond("/inbox").intent == "gtd_inspect"
    assert provider.analyze_and_respond("/dday").intent == "dday_inspect"
    assert provider.analyze_and_respond("/briefing").intent == "task_briefing"
    assert provider.analyze_and_respond("/briefing morning").intent == "task_briefing_morning"
    assert provider.analyze_and_respond("/briefing evening").intent == "task_briefing_evening"
    assert provider.analyze_and_respond("/schedule").intent == "briefing_schedule_inspect"
    assert provider.analyze_and_respond("/commit").intent == "repo_commit"
    assert provider.analyze_and_respond("/push").intent == "repo_push"
    assert provider.analyze_and_respond("/sync").intent == "repo_sync"
    assert provider.analyze_and_respond("/weekly").intent == "weekly_review"
    assert provider.analyze_and_respond("/heatmap").intent == "lifelog_heatmap"
    assert provider.analyze_and_respond("/edit 2026-09-15").intent == "lifelog_edit"
    assert provider.analyze_and_respond("/status").intent == "log_status_inspect"

    res_log = provider.analyze_and_respond("/log 내일 아침 10시 미팅 준비")
    assert res_log.intent == "log_explicit"
    assert "미팅 준비" in (res_log.log_content or "")

    res_done = provider.analyze_and_respond("/done 세무 신고")
    assert res_done.intent == "task_complete"
    assert res_done.log_content == "세무 신고"


def test_llm_provider_pending_draft_confirm_and_reject():
    """Vision 사진 분석 카드 등 보류 중인 초안(pending_log)에 대한 짧은 승인/거절 토큰 처리 검증."""
    provider = LLMProvider(fast_mode=True)
    pending = {"content": "한강 러닝 5km", "category": "Workout & Health"}

    res_confirm = provider.analyze_and_respond("응 좋아", pending_log=pending)
    assert res_confirm.intent == "log_confirm"
    assert res_confirm.log_content == "한강 러닝 5km"

    res_reject = provider.analyze_and_respond("아니", pending_log=pending)
    assert res_reject.intent == "log_reject"


def test_skill_md_full_injection_in_system_prompt():
    """ADR-066: 연결된 GTD 저장소의 .agents/skills/gtd-assistant/SKILL.md 원문이 프롬프트에 그대로 주입되고 [INTENT: ...] 강제 태그가 제거되었는지 검증."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = os.path.join(tmpdir, ".agents", "skills", "gtd-assistant")
        os.makedirs(skill_dir, exist_ok=True)
        skill_path = os.path.join(skill_dir, "SKILL.md")
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write("# GTD Assistant Skill\n- gtd/someday_maybe.md\n- gtd/waiting_for.md\n")

        loaded = load_skill_instructions(tmpdir)
        assert "gtd/someday_maybe.md" in loaded
        assert "gtd/waiting_for.md" in loaded

        sys_prompt = build_system_prompt("은퇴 계획 일정을 someday로 이동시켜줘", gtd_path=tmpdir)
        assert "gtd/someday_maybe.md" in sys_prompt
        assert "[INTENT: log_suggest" not in sys_prompt
