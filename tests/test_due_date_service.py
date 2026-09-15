import os
import tempfile
from datetime import date

from app.services.due_date_service import DueDateService
from app.services.llm_provider import LLMProvider


def test_extract_due_date_tags():
    base = date(2026, 9, 15)  # 화요일 (Tuesday)

    # 1. 명시적 전체 태그
    d, text = DueDateService.extract_due_date_from_text("세무 신고 ~2026-09-20 완료하기", base_date=base)
    assert d == date(2026, 9, 20)
    assert text == "세무 신고 ~2026-09-20 완료하기"

    # 2. @due() 태그
    d2, _ = DueDateService.extract_due_date_from_text("보고서 제출 @due(2026-09-18)", base_date=base)
    assert d2 == date(2026, 9, 18)

    # 3. (마감: YYYY-MM-DD) 태그
    d3, _ = DueDateService.extract_due_date_from_text("엔진 오일 교체 (마감: 2026-09-25)", base_date=base)
    assert d3 == date(2026, 9, 25)

    # 4. ~MM-DD 축약 태그
    d4, text4 = DueDateService.extract_due_date_from_text("치과 진료 ~09-22", base_date=base)
    assert d4 == date(2026, 9, 22)
    assert "~2026-09-22" in text4


def test_extract_due_date_korean_relative():
    base = date(2026, 9, 15)  # 화요일 (Tuesday, weekday=1)

    # 오늘까지
    d_today, text_today = DueDateService.extract_due_date_from_text("오늘까지 결제 완료하기", base_date=base)
    assert d_today == date(2026, 9, 15)
    assert "~2026-09-15" in text_today

    # 내일까지
    d_tmr, text_tmr = DueDateService.extract_due_date_from_text("내일까지 보고서 제출", base_date=base)
    assert d_tmr == date(2026, 9, 16)
    assert "~2026-09-16" in text_tmr

    # 모레까지
    d_day_after, _ = DueDateService.extract_due_date_from_text("모레까지 회의 아젠다 정리", base_date=base)
    assert d_day_after == date(2026, 9, 17)

    # 이번 주 금요일까지 (화요일 기준 -> 금요일: +3일 -> 9월 18일)
    d_fri, _ = DueDateService.extract_due_date_from_text("이번 주 금요일까지 디자인 시안 검토", base_date=base)
    assert d_fri == date(2026, 9, 18)

    # 다음 주 수요일까지 (화요일 기준 -> 다음 주 수요일: 6 + 2 = +8일 -> 9월 23일)
    d_next_wed, _ = DueDateService.extract_due_date_from_text("다음 주 수요일까지 자동차 정기검사 예약", base_date=base)
    assert d_next_wed == date(2026, 9, 23)

    # 9월 30일까지
    d_month, _ = DueDateService.extract_due_date_from_text("9월 30일까지 연말정산 서류 제출", base_date=base)
    assert d_month == date(2026, 9, 30)

    # 5일 뒤까지
    d_offset, _ = DueDateService.extract_due_date_from_text("5일 뒤까지 택배 반품 신청", base_date=base)
    assert d_offset == date(2026, 9, 20)


def test_calculate_dday():
    base = date(2026, 9, 15)

    # Overdue (기한 초과)
    res_overdue = DueDateService.calculate_dday(date(2026, 9, 12), base_date=base)
    assert res_overdue["status"] == "overdue"
    assert res_overdue["diff_days"] == -3
    assert "기한 초과 (D+3)" in res_overdue["label"]
    assert res_overdue["priority_weight"] > 100

    # Today (오늘 마감)
    res_today = DueDateService.calculate_dday(date(2026, 9, 15), base_date=base)
    assert res_today["status"] == "today"
    assert res_today["diff_days"] == 0
    assert "오늘 마감 (D-Day)" in res_today["label"]

    # Urgent (마감 임박 D-1 ~ D-3)
    res_urgent = DueDateService.calculate_dday(date(2026, 9, 17), base_date=base)
    assert res_urgent["status"] == "urgent"
    assert res_urgent["diff_days"] == 2
    assert "마감 임박 (D-2)" in res_urgent["label"]

    # Upcoming (예정 D-4+)
    res_upcoming = DueDateService.calculate_dday(date(2026, 9, 25), base_date=base)
    assert res_upcoming["status"] == "upcoming"
    assert res_upcoming["diff_days"] == 10
    assert "D-10" in res_upcoming["label"]


def test_scan_gtd_due_tasks_and_prioritization():
    base = date(2026, 9, 15)

    with tempfile.TemporaryDirectory() as tmp_dir:
        gtd_dir = os.path.join(tmp_dir, "gtd")
        os.makedirs(gtd_dir, exist_ok=True)

        next_actions_content = """# Next Actions

- [ ] 세무 신고 ~2026-09-12
- [ ] 오늘 마감 과제 ~2026-09-15
- [ ] 급하지 않은 과제
- [ ] 내일 마감 과제 ~2026-09-16
- [ ] 10일 뒤 마감 과제 ~2026-09-25
- [x] 이미 완료된 과제 ~2026-09-10
"""
        with open(os.path.join(gtd_dir, "next_actions.md"), "w", encoding="utf-8") as f:
            f.write(next_actions_content)

        inbox_content = """# Inbox

- [ ] 인박스 급한 과제 ~2026-09-17
"""
        with open(os.path.join(gtd_dir, "inbox.md"), "w", encoding="utf-8") as f:
            f.write(inbox_content)

        scan_res = DueDateService.scan_gtd_due_tasks(tmp_dir, base_date=base)
        assert scan_res["total_count"] == 5
        assert scan_res["overdue_count"] == 1  # 09-12
        assert scan_res["today_count"] == 1    # 09-15
        assert scan_res["urgent_count"] == 2   # 09-16, 09-17
        assert scan_res["upcoming_count"] == 1 # 09-25

        # D-Day 알림 마크다운 섹션 생성 검증
        briefing_section = DueDateService.format_dday_briefing_section(tmp_dir, base_date=base)
        assert "GTD 마감일 & D-Day 알림" in briefing_section
        assert "기한 초과" in briefing_section
        assert "오늘 마감" in briefing_section
        assert "마감 임박" in briefing_section

        # 독립 마감 리포트 생성 검증
        report = DueDateService.format_standalone_deadline_report(tmp_dir, base_date=base)
        assert "GTD 마감일(D-Day) 현황 종합 리포트" in report
        assert "기한초과: **1개**" in report
        assert "오늘마감: **1개**" in report

        # Next Actions 우선순위 정렬 검증
        raw_actions = [
            "급하지 않은 일반 과제",
            "10일 뒤 과제 ~2026-09-25",
            "세무 신고 ~2026-09-12",
            "오늘 마감 과제 ~2026-09-15",
            "내일 마감 과제 ~2026-09-16",
        ]
        prioritized = DueDateService.prioritize_next_actions(raw_actions, base_date=base)
        # 우선순위: 기한초과(09-12) -> 오늘마감(09-15) -> 임박(09-16) -> 예정(09-25) -> 일반
        assert "세무 신고" in prioritized[0]
        assert "오늘 마감" in prioritized[1]
        assert "내일 마감" in prioritized[2]


def test_llm_provider_dday_intent_and_actionable_task():
    provider = LLMProvider()

    # 1. D-Day 슬래시 커맨드 및 자연어 인텐트 분석
    res1 = provider.analyze_and_respond("/dday")
    assert res1.intent == "dday_inspect"

    res2 = provider.analyze_and_respond("/deadline")
    assert res2.intent == "dday_inspect"

    res3 = provider.analyze_and_respond("마감일 확인해줘")
    assert res3.intent == "dday_inspect"

    res4 = provider.analyze_and_respond("D-day 현황 알려줘")
    assert res4.intent == "dday_inspect"

    res5 = provider.analyze_and_respond("마감 임박한 할 일 뭐야?")
    assert res5.intent == "dday_inspect"

    # 2. _extract_actionable_task의 마감일 자동 태깅 검증
    # (2-1) 명시적 태그
    task1 = provider._extract_actionable_task("세무 신고 ~2026-09-20 gtd에 넣어줘")
    assert "~2026-09-20" in task1

    # (2-2) 한국어 상대일자 ("내일까지 보고서 제출")
    task2 = provider._extract_actionable_task("내일까지 분기 실적 보고서 제출 gtd에 기록해")
    assert "~202" in task2  # 연도 태그 자동 생성
    assert "보고서" in task2
