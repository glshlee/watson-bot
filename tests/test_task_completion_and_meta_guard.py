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


def test_colloquial_task_completion_intent():
    """ADR-031: 구어체 태스크 완료 보고 발화의 task_complete 의도 분류 검증."""
    llm = LLMProvider()

    res1 = llm.analyze_and_respond("민방위 사이버교육은 완료했어.")
    assert res1.intent == "task_complete"
    assert "민방위" in res1.log_content

    res2 = llm.analyze_and_respond("민방위 사이버교육 완료 gtd에 기록해.")
    assert res2.intent == "task_complete"
    assert "민방위" in res2.log_content

    res3 = llm.analyze_and_respond("사이버교육 다했어")
    assert res3.intent == "task_complete"
    assert "사이버교육" in res3.log_content

    res4 = llm.analyze_and_respond("휴지랑 원두 구매 완료 인박스에 체크해줘")
    assert res4.intent == "task_complete"


def test_meta_feedback_and_protest_guardrail():
    """ADR-031: 사용자 항의/메타 피드백이 log_suggest(일기 초안)로 오인되지 않고 지능형 복구됨을 검증."""
    llm = LLMProvider()

    history = [
        {"role": "user", "content": "민방위 사이버교육 완료 gtd에 기록해."},
        {"role": "assistant", "content": "요청하신 태스크를 GTD 수집함에 등록했습니다!"},
    ]

    protest_prompt = "아니 이미 인박스에 있다면서. 그래서 완료했다고 말한건데?"
    res = llm.analyze_and_respond(protest_prompt, history=history)

    # 절대로 log_suggest 초안 카드가 떠서는 안 됨!
    assert res.intent != "log_suggest"
    # 완료 의도가 담긴 항의이므로 task_complete로 자동 복구
    assert res.intent == "task_complete"
    assert "민방위" in res.log_content


def test_complete_matching_tasks_fuzzy_and_predicate_stripping(temp_gtd_env):
    """ADR-031: AgentService.complete_matching_tasks의 서술어 정제 및 부분 매칭 검증."""
    agent_service = AgentService(base_dir=temp_gtd_env)

    # 1. '민방위 사이버교육은 완료했어' 구어체로 '민방위 사이버 교육 이수 여부 확인' 완료 처리 검증
    completed = agent_service.complete_matching_tasks(["민방위 사이버교육은 완료했어"])
    assert len(completed) >= 1
    assert any("민방위 사이버 교육" in t for t in completed)

    # 2. 실제 inbox.md 파일에 - [x] 로 반영되었는지 확인
    inbox_file = os.path.join(temp_gtd_env, "gtd", "inbox.md")
    with open(inbox_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "- [x] 민방위 사이버 교육 이수 여부 확인 🛡️💻" in content
