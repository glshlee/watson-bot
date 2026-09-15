import os
import tempfile
from datetime import datetime

from app.services.llm_provider import LLMProvider
from app.services.search_service import SearchService
from app.services.weekly_review_service import WeeklyReviewService


def test_search_service_basic_and_highlight():
    with tempfile.TemporaryDirectory() as tmpdir:
        daily_dir = os.path.join(tmpdir, "logs", "daily")
        os.makedirs(daily_dir, exist_ok=True)
        gtd_dir = os.path.join(tmpdir, "gtd")
        os.makedirs(gtd_dir, exist_ok=True)

        # 1. 일일 로그 생성
        log_2026_09_08 = os.path.join(daily_dir, "2026-09-08.md")
        with open(log_2026_09_08, "w", encoding="utf-8") as f:
            f.write(
                "# 2026-09-08\n\n"
                "## 📝 오늘 하루 일상 및 기록 (Daily Journal)\n"
                "- [15:22] 서산쪽으로 여행을 가보려구. 용현집이라고 어죽을 파는 곳을 좋아했거든? 게국지 집에도 가보고싶대.\n\n"
                "## 🏃 운동 & 건강 (Workout)\n"
                "- [19:30] 야간 러닝 5km 완주 및 스트레칭 완료\n"
            )

        # 2. GTD Inbox 생성
        inbox_file = os.path.join(gtd_dir, "inbox.md")
        with open(inbox_file, "w", encoding="utf-8") as f:
            f.write(
                "# 📥 GTD Inbox\n\n"
                "## 🧘 개인 생활\n"
                "- [ ] 서산 여행 계획 및 맛집 방문 (용현집 어죽, 또간집 게국지) 🚗🍲\n"
                "- [ ] 자동차 정기검사 예약 ~2026-09-24\n"
            )

        svc = SearchService(base_dir=tmpdir)

        # 단일 키워드 검색
        results_seosan = svc.search("서산")
        assert len(results_seosan) == 2
        # 스니펫에 **서산** 하이라이트 포함 확인
        assert any("**서산**" in r["snippet"] for r in results_seosan)
        # 일일 로그 일자 추출 확인
        daily_match = next(r for r in results_seosan if r["date"] == "2026-09-08")
        assert "용현집" in daily_match["snippet"]
        assert daily_match["section"] == "📝 오늘 하루 일상 및 기록 (Daily Journal)"

        # 다중 키워드 (AND) 검색
        results_multi = svc.search("서산 어죽")
        assert len(results_multi) == 2
        assert all("서산" in r["line_content"] and "어죽" in r["line_content"] for r in results_multi)

        # 러닝 검색
        results_running = svc.search("러닝")
        assert len(results_running) == 1
        assert "5km" in results_running[0]["snippet"]

        # 없는 키워드 검색
        results_empty = svc.search("존재하지않는외계단어123")
        assert len(results_empty) == 0

        # 마크다운 카드 포맷팅
        card = svc.format_search_results_card("서산", results_seosan)
        assert "총 2건" in card
        assert "2026-09-08" in card
        assert "gtd/inbox.md" in card


def test_search_service_empty_and_edge_cases():
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = SearchService(base_dir=tmpdir)
        assert svc.search("") == []
        assert svc.search("   ") == []

        empty_card = svc.format_search_results_card("테스트", [])
        assert "일치하는 기록을 찾지 못했습니다" in empty_card


def test_weekly_review_service_metrics():
    with tempfile.TemporaryDirectory() as tmpdir:
        daily_dir = os.path.join(tmpdir, "logs", "daily")
        os.makedirs(daily_dir, exist_ok=True)
        gtd_dir = os.path.join(tmpdir, "gtd")
        os.makedirs(gtd_dir, exist_ok=True)

        # 9월 10일: 운동 + 업무
        with open(os.path.join(daily_dir, "2026-09-10.md"), "w", encoding="utf-8") as f:
            f.write(
                "# 2026-09-10\n\n"
                "## 🏢 업무 & 개발\n"
                "- [11:00] Databricks 파이프라인 아키텍처 회의 및 배포 점검\n\n"
                "## 🏃 운동\n"
                "- [20:00] 헬스장 웨이트 트레이닝 및 스쿼트 80kg\n\n"
                "## ✅ 오늘 완료한 일\n"
                "- [x] 1분기 결산 보고서 작성 완료\n"
            )

        # 9월 12일: 일기 + 완료 태스크
        with open(os.path.join(daily_dir, "2026-09-12.md"), "w", encoding="utf-8") as f:
            f.write(
                "# 2026-09-12\n\n"
                "## 📝 오늘 하루 일상 및 기록\n"
                "- [08:20] 아내를 위해 따뜻한 미역국을 정성껏 준비함\n\n"
                "## ✅ 오늘 완료한 일\n"
                "- [x] 미역국 끓이기 및 영양식 챙기기\n"
                "- [x] 민방위 사이버교육 이수 🛡️\n"
            )

        # 9월 15일: 오늘 로그
        with open(os.path.join(daily_dir, "2026-09-15.md"), "w", encoding="utf-8") as f:
            f.write(
                "# 2026-09-15\n\n"
                "## 💡 순간 메모 / 캡처\n"
                "- [14:00] AI 에이전트 주간 결산 기능 기획 아이디어\n\n"
                "## ✅ 오늘 완료한 일\n"
                "- [x] Watson Phase 42 구현 완료\n"
            )

        # GTD Inbox
        with open(os.path.join(gtd_dir, "inbox.md"), "w", encoding="utf-8") as f:
            f.write(
                "# 📥 GTD Inbox\n\n"
                "## 🧘 개인 생활\n"
                "- [ ] 서산 여행 계획 세우기\n"
                "- [ ] 베란다 전등 교체\n"
            )

        svc = WeeklyReviewService(base_dir=tmpdir)
        # 기준일 2026-09-15 (7일간: 2026-09-09 ~ 2026-09-15)
        ref_dt = datetime(2026, 9, 15, 21, 0, 0)  # noqa: DTZ001
        data = svc.collect_weekly_data(ref_date=ref_dt, days=7)

        assert data["total_days"] == 7
        assert data["recorded_days"] == 3  # 10일, 12일, 15일 3일
        assert data["record_rate"] == 43  # 3/7 ~= 43%
        assert data["total_completed"] == 4  # 1개 + 2개 + 1개 = 4개
        assert len(data["completed_tasks"]) == 4
        assert data["inbox_pending_count"] == 2
        assert "서산 여행 계획 세우기" in data["inbox_items"]

        # 카테고리 카운트 검증
        assert data["categories"]["workout_count"] >= 1
        assert data["categories"]["work_count"] >= 1
        assert data["categories"]["idea_count"] >= 1

        # 주간 회고 리포트 마크다운 생성 검증
        review_result = svc.generate_weekly_review(ref_date=ref_dt, days=7)
        md = review_result["markdown"]
        assert "📊 **[왓슨 주간 결산 리포트 (Weekly Review)]**" in md
        assert "총 7일 중 **3일** 기록 완료" in md
        assert "총 **4개** 완료" in md
        assert "1분기 결산 보고서" in md
        assert "미역국 끓이기" in md
        assert "Watson Phase 42 구현 완료" in md
        assert "수집함에 정리 대기 중인 항목이 **2개** 있습니다" in md
        assert "왓슨의 주간 한마디" in md


def test_intent_classification_search_and_weekly():
    provider = LLMProvider()

    # 1. /search 슬래시 커맨드
    res1 = provider.analyze_and_respond("/search 서산 맛집")
    assert res1.intent == "search_query"
    assert res1.log_content == "서산 맛집"

    res2 = provider.analyze_and_respond("/find 미역국")
    assert res2.intent == "search_query"
    assert res2.log_content == "미역국"

    # 2. 자연어 검색 질의
    res3 = provider.analyze_and_respond("지난달 서산 맛집 찾아줘")
    assert res3.intent == "search_query"
    assert "서산 맛집" in (res3.log_content or "")

    res4 = provider.analyze_and_respond("과거 일기에서 운동 기록 찾아봐")
    assert res4.intent == "search_query"
    assert "운동" in (res4.log_content or "")

    # 3. /weekly 슬래시 커맨드
    res5 = provider.analyze_and_respond("/weekly")
    assert res5.intent == "weekly_review"

    res6 = provider.analyze_and_respond("/review")
    assert res6.intent == "weekly_review"

    # 4. 자연어 주간 결산
    res7 = provider.analyze_and_respond("주간 결산 알려줘")
    assert res7.intent == "weekly_review"

    res8 = provider.analyze_and_respond("이번 주 회고 보여줘")
    assert res8.intent == "weekly_review"
