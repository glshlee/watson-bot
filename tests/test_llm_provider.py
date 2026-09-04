from app.services.llm_provider import LLMProvider


def test_llm_provider_chat_only():
    provider = LLMProvider()
    res = provider.analyze_and_respond("안녕? 오늘 날씨 어때?")
    assert res.intent == "chat_only"
    assert "안녕하세요" in res.ai_response or "하루" in res.ai_response
    assert res.log_content is None


def test_llm_provider_workout_suggest():
    provider = LLMProvider()
    res = provider.analyze_and_respond("오늘 퇴근하고 헬스장에서 스쿼트 100kg 성공했어!")
    assert res.intent == "log_suggest"
    assert res.category == "Workout & Health"
    assert "스쿼트 100kg" in res.log_content
    assert "기록해 둘까요" in res.ai_response


def test_llm_provider_confirm_and_reject():
    provider = LLMProvider()
    pending = {"content": "한강 러닝 5km", "category": "Workout & Health"}

    # 승인
    res_confirm = provider.analyze_and_respond("응 좋아", pending_log=pending)
    assert res_confirm.intent == "log_confirm"
    assert res_confirm.log_content == "한강 러닝 5km"
    assert res_confirm.category == "Workout & Health"

    # 거절
    res_reject = provider.analyze_and_respond("아니 괜찮아", pending_log=pending)
    assert res_reject.intent == "log_reject"
    assert res_reject.log_content is None


def test_llm_provider_explicit_command():
    provider = LLMProvider()
    res = provider.analyze_and_respond("/log 내일 아침 10시 미팅 준비")
    assert res.intent == "log_explicit"
    assert "미팅 준비" in res.log_content
