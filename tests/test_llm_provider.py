from app.services.llm_provider import LLMProvider


def test_llm_provider_chat_only():
    provider = LLMProvider()
    res = provider.analyze_and_respond("안녕? 오늘 날씨 어때?")
    assert res.intent == "chat_only"
    assert len(res.ai_response.strip()) > 5
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


def test_llm_provider_repo_push():
    provider = LLMProvider()
    for prompt in ["푸시해줘", "푸시도 해줘", "푸시가 안됐는데 다시 확인해줘", "/push", "깃 푸시"]:
        res = provider.analyze_and_respond(prompt)
        assert res.intent == "repo_push", f"Failed for {prompt}"

    # "푸시업"은 운동 제안으로 가야 함
    res_pushup = provider.analyze_and_respond("오늘 헬스장에서 푸시업 100개 완료")
    assert res_pushup.intent == "log_suggest"
    assert res_pushup.category == "Workout & Health"


def test_llm_provider_conversational_directive_resolution():
    provider = LLMProvider()
    history = [
        {"role": "user", "content": "오늘은 내가 카카오페이에 처음 왔을 때 나의 버디였던 고든이 퇴사하는 날이야. 고마웠는데 아쉽네."},
        {"role": "assistant", "content": "첫 버디의 퇴사라니 참 섭섭하고 허전하시겠습니다."},
    ]
    for prompt in ["응 오늘 로그에 기록해줘", "응 로그에 기록해줘", "오늘 로그에 기록해줘", "이 내용 오늘 일기에 적어줘"]:
        res = provider.analyze_and_respond(prompt, history=history)
        assert res.intent == "log_explicit", f"Failed for {prompt}"
        assert "고든이 퇴사하는 날" in res.log_content, f"Content mismatch for {prompt}: {res.log_content}"

