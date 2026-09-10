import os
import shutil
import tempfile
from datetime import datetime

from app.config import get_app_timezone
from app.services.briefing_service import BriefingService
from app.services.llm_provider import LLMProvider


def test_detect_briefing_mode():
    kst = get_app_timezone()
    service = BriefingService()

    # 명시적 오버라이드 검증
    assert service.detect_briefing_mode("morning") == "morning"
    assert service.detect_briefing_mode("am") == "morning"
    assert service.detect_briefing_mode("아침 브리핑") == "morning"
    assert service.detect_briefing_mode("evening") == "evening"
    assert service.detect_briefing_mode("pm") == "evening"
    assert service.detect_briefing_mode("저녁 회고") == "evening"

    # 시간대 기반 자동 판별 검증 (오전 05:00 ~ 13:59: morning, 14:00 이후: evening)
    morning_time = datetime(2026, 9, 10, 8, 30, tzinfo=kst)
    assert service.detect_briefing_mode(date_obj=morning_time) == "morning"

    lunch_time = datetime(2026, 9, 10, 13, 59, tzinfo=kst)
    assert service.detect_briefing_mode(date_obj=lunch_time) == "morning"

    afternoon_time = datetime(2026, 9, 10, 14, 0, tzinfo=kst)
    assert service.detect_briefing_mode(date_obj=afternoon_time) == "evening"

    night_time = datetime(2026, 9, 10, 21, 30, tzinfo=kst)
    assert service.detect_briefing_mode(date_obj=night_time) == "evening"


def test_read_briefing_context_and_generate_morning_briefing():
    temp_dir = tempfile.mkdtemp()
    try:
        kst = get_app_timezone()
        date_obj = datetime(2026, 9, 10, 9, 0, tzinfo=kst)

        # GTD 디렉토리 및 파일 생성
        os.makedirs(os.path.join(temp_dir, "gtd"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "logs", "daily"), exist_ok=True)

        with open(os.path.join(temp_dir, "gtd", "inbox.md"), "w", encoding="utf-8") as f:
            f.write("# Inbox\n\n- [ ] 새로운 책 구매 검토\n- [ ] 치과 정기 검진 예약\n")

        with open(os.path.join(temp_dir, "gtd", "next_actions.md"), "w", encoding="utf-8") as f:
            f.write("# Next Actions\n\n- [ ] 🚨 Phase 24 브리핑 기능 구현 배포\n- [ ] 주간 엔지니어링 리포트 작성\n- [ ] 팀 주간 회의 참석\n")

        with open(os.path.join(temp_dir, "logs", "daily", "2026-09-10.md"), "w", encoding="utf-8") as f:
            f.write("# 2026-09-10\n\n## 📅 주요 일정\n- 10:00 데일리 스크럼\n- 15:00 아키텍처 리뷰\n")

        service = BriefingService(base_dir=temp_dir)
        ctx = service.read_briefing_context(date_obj=date_obj)

        assert ctx["date_str"] == "2026-09-10"
        assert len(ctx["next_actions"]) == 3
        assert len(ctx["inbox_items"]) == 2
        assert len(ctx["schedule_items"]) == 2

        # Morning 브리핑 생성 (use_ai=False로 결정론적 룰 기반 검증)
        res = service.generate_briefing(mode="morning", date_obj=date_obj, use_ai=False)
        assert res["mode"] == "morning"
        assert res["date"] == "2026-09-10"
        md = res["markdown"]

        assert "Watson Morning Briefing" in md
        assert "오늘의 집중 우선순위 Top 3" in md
        assert "Phase 24 브리핑 기능 구현 배포" in md
        assert "추천 실행 순서 (Schedule & Flow)" in md
        assert "수집함 정리 안내 (Inbox)" in md
        assert "새로운 책 구매 검토" in md
    finally:
        shutil.rmtree(temp_dir)


def test_generate_evening_briefing():
    temp_dir = tempfile.mkdtemp()
    try:
        kst = get_app_timezone()
        date_obj = datetime(2026, 9, 10, 19, 0, tzinfo=kst)

        os.makedirs(os.path.join(temp_dir, "gtd"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "logs", "daily"), exist_ok=True)

        with open(os.path.join(temp_dir, "gtd", "next_actions.md"), "w", encoding="utf-8") as f:
            f.write("# Next Actions\n\n- [ ] 잔여 버그 픽스\n")

        with open(os.path.join(temp_dir, "logs", "daily", "2026-09-10.md"), "w", encoding="utf-8") as f:
            f.write("# 2026-09-10\n\n## ✅ 오늘 완료한 일\n- [x] 모바일 레이아웃 최적화 완료\n- [x] 테스트 스위트 전원 통과\n")

        service = BriefingService(base_dir=temp_dir)
        res = service.generate_briefing(mode="evening", date_obj=date_obj, use_ai=False)

        assert res["mode"] == "evening"
        md = res["markdown"]

        assert "Watson Evening Briefing & 일과 회고" in md
        assert "오늘 완료된 작업 하이라이트" in md
        assert "모바일 레이아웃 최적화 완료" in md
        assert "미완료 / 진행 중 과제 현황" in md
        assert "내일 아침 가장 먼저 마주할 핵심 과제 (Priority 1)" in md
        assert "잔여 버그 픽스" in md
    finally:
        shutil.rmtree(temp_dir)


def test_llm_provider_briefing_intent_classification():
    provider = LLMProvider()

    # 1. 명시적 슬래시 커맨드
    res_m = provider.analyze_and_respond("/briefing morning")
    assert res_m.intent == "task_briefing_morning"

    res_e = provider.analyze_and_respond("/briefing evening")
    assert res_e.intent == "task_briefing_evening"

    res_auto = provider.analyze_and_respond("/briefing")
    assert res_auto.intent == "task_briefing"

    # 2. 자연어 의도
    res_nlp_m = provider.analyze_and_respond("오늘 아침 브리핑 해줘")
    assert res_nlp_m.intent == "task_briefing_morning"

    res_nlp_e = provider.analyze_and_respond("오늘 저녁 일과 회고 정리해줘")
    assert res_nlp_e.intent == "task_briefing_evening"

    res_nlp_general = provider.analyze_and_respond("오늘 할 일 브리핑해줘")
    assert res_nlp_general.intent == "task_briefing"
