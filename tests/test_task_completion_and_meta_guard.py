import os
import tempfile

import pytest

from app.services.agent_service import AgentService
from app.services.llm_provider import LLMProvider


@pytest.fixture
def temp_gtd_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        gtd_dir = os.path.join(tmpdir, "gtd")
        logs_dir = os.path.join(tmpdir, "logs", "daily")
        os.makedirs(gtd_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)

        inbox_path = os.path.join(gtd_dir, "inbox.md")
        with open(inbox_path, "w", encoding="utf-8") as f:
            f.write(
                "# 📥 Inbox\n\n"
                "## 🧘 개인 생활 & 건강\n"
                "- [ ] 민방위 사이버 교육 이수 여부 확인 🛡️💻\n"
                "- [ ] 구매 목록: 두루마리 휴지, 커피원두, 고양이모래 🛒\n"
            )

        yield tmpdir


def test_slash_done_command_and_natural_delegation():
    """ADR-066: /done 슬래시 명령어는 task_complete로, 자연어는 파이썬 인텐트 분류 없이 LLM(chat_only)으로 위임됨을 검증."""
    llm = LLMProvider(fast_mode=True)

    res_slash = llm.analyze_and_respond("/done 민방위 사이버교육")
    assert res_slash.intent == "task_complete"
    assert "민방위" in (res_slash.log_content or "")

    res_natural = llm.analyze_and_respond("민방위 사이버교육은 완료했어.")
    assert res_natural.intent == "chat_only"


def test_complete_matching_tasks_fuzzy_and_predicate_stripping(temp_gtd_env):
    """ADR-031: AgentService.complete_matching_tasks의 서술어 정제 및 부분 매칭 검증."""
    agent_service = AgentService(base_dir=temp_gtd_env)

    # 1. '민방위 사이버교육은 완료했어' 구어체로 '민방위 사이버 교육 이수 여부 확인' 완료 처리 검증
    completed = agent_service.complete_matching_tasks(["민방위 사이버교육은 완료했어"])
    assert len(completed) >= 1
    assert any("민방위 사이버 교육" in t for t in completed)

    # 2. ADR-032: 스킬 규칙에 따라 inbox.md 파일에서는 잘라내어(Cut) 제거되었는지 확인
    inbox_file = os.path.join(temp_gtd_env, "gtd", "inbox.md")
    with open(inbox_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "민방위 사이버 교육 이수 여부 확인" not in content
    assert "- [ ] 구매 목록: 두루마리 휴지, 커피원두, 고양이모래 🛒" in content

    # 3. ADR-032: 당일 데일리 로그 파일의 '## ✅ 오늘 완료한 일 (Completed GTD Tasks)'에 이관(Paste)되었는지 확인
    daily_log_file = agent_service.get_lifelog_filepath()
    assert os.path.exists(daily_log_file)
    with open(daily_log_file, "r", encoding="utf-8") as f:
        daily_content = f.read()
    assert "- [x] 민방위 사이버 교육 이수 여부 확인 🛡️💻" in daily_content
    assert "## ✅ 오늘 완료한 일 (Completed GTD Tasks)" in daily_content
