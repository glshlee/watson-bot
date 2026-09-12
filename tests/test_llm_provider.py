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


def test_llm_provider_dual_logging_and_task_extraction():
    provider = LLMProvider()
    prompt = (
        "회사에서 리조트를 신청할 수 있거든? 와이프와 가려고 부여리조트를 신청했는데 떨어졌어. "
        "그래서 그냥 서산쪽으로 여행을 가보려구. 용현집이라고 어죽을 파는 곳을 좋아했거든? "
        "그래서 거기를 가보고싶고, 또간집에 나온 게국지 집에도 가보고싶대. 로그와 gtd에 기록해줘."
    )
    res = provider.analyze_and_respond(prompt)
    assert res.intent == "log_dual"
    assert res.is_dual_log is True
    assert "로그와 gtd에" not in res.log_content
    assert not res.log_content.endswith(".")
    assert "서산" in res.gtd_task_content
    assert "여행" in res.gtd_task_content
    assert "용현집" in res.gtd_task_content


def test_llm_provider_log_status_inspect():
    provider = LLMProvider()
    queries = [
        "오늘 로그 파일에 기록했어?",
        "오늘 로그에 기록했어?",
        "오늘 일기 적었어?",
        "기록했어?",
        "기록됐어?",
        "기록된거 맞아?",
        "기록 확인",
        "오늘 기록 확인",
        "일기 확인해줘",
        "기록 됐니?",
    ]
    for q in queries:
        res = provider.analyze_and_respond(q)
        assert res.intent == "log_status_inspect", f"Failed for query '{q}': got {res.intent}"


def test_llm_provider_front_placed_directive():
    provider = LLMProvider()
    prompt = (
        "아니 어제 gtd에 이 내용을 넣어달라구\n\n"
        "어제 이야기를 좀 해도 될까. 어제 와이프랑 산부인과에 초음파를 보러 갔는데, 아기가 심장이 멈췄대. "
        "그래서 급하게 병원을 잡아서 소파술을 하고왔어."
    )
    res = provider.analyze_and_respond(prompt)
    assert res.intent == "log_explicit"
    assert "산부인과" in res.log_content or "소파술" in res.log_content
    assert res.category == "GTD Inbox"


def test_llm_provider_update_context_directive_not_sync():
    provider = LLMProvider()
    history = [
        {"role": "user", "content": "어제 와이프랑 산부인과에 초음파를 보러 갔는데 소파술을 하고 왔어."},
        {"role": "assistant", "content": "정말 가슴 아프셨겠습니다. 위로를 드립니다."},
    ]
    prompt = "어제 gtd에 업데이트 해줘 위ㅡ내용"
    res = provider.analyze_and_respond(prompt, history=history)
    assert res.intent == "log_explicit"
    assert "산부인과" in res.log_content


def test_llm_provider_life_moment_draft_preview():
    provider = LLMProvider()
    prompt = "오늘은 아침에 일어나서 와이프를 위한 미역국을 끓였어"
    res = provider.analyze_and_respond(prompt)
    assert res.intent == "log_suggest"
    assert res.category == "Daily Notes & Diary"
    assert "라이프로그 초안" in res.ai_response
    assert "미역국" in res.ai_response
    assert "기록해 둘까요" in res.ai_response


def test_llm_provider_dual_confirm_from_pending():
    provider = LLMProvider()
    pending = {
        "content": "아내 수술 후 퇴원 및 저녁 미역국 식사",
        "category": "Daily Notes & Diary",
        "gtd_task": "아내 신체 회복을 위한 영양식 및 보온 챙기기",
        "is_dual": True,
    }
    for confirm_prompt in ["응", "이대로 해줘", "좋아", "이대로 기록해줘", "응 좋아"]:
        res = provider.analyze_and_respond(confirm_prompt, pending_log=pending)
        assert res.intent == "log_dual", f"Failed for {confirm_prompt}"
        assert res.is_dual_log is True
        assert "영양식" in (res.gtd_task_content or "")




