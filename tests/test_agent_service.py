import os
import shutil
import tempfile
from datetime import datetime, timezone

from app.config import get_app_timezone
from app.services.agent_service import AgentService


def test_append_or_update_lifelog():
    temp_dir = tempfile.mkdtemp()
    try:
        service = AgentService(base_dir=temp_dir)
        kst = get_app_timezone()
        now = datetime(2026, 8, 28, 14, 30, tzinfo=kst)

        filepath = service.append_or_update_lifelog(
            content="Today I completed Phase 2 architecture for Watson.",
            category="Daily Notes & Diary",
            date_obj=now,
        )

        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# 📅 Life Log - 2026-08-28" in content
        assert "## 📝 Daily Notes & Diary" in content
        assert "- [14:30] Today I completed Phase 2 architecture for Watson." in content
    finally:
        shutil.rmtree(temp_dir)


def test_timezone_conversion_utc_to_kst():
    temp_dir = tempfile.mkdtemp()
    try:
        # Create daily logs structure
        os.makedirs(os.path.join(temp_dir, "logs", "daily"), exist_ok=True)
        service = AgentService(base_dir=temp_dir)

        # 05:13 UTC should convert to 14:13 KST
        utc_dt = datetime(2026, 9, 8, 5, 13, tzinfo=timezone.utc)
        filepath = service.append_or_update_lifelog(
            content="고든의 퇴사 이야기",
            category="Daily Notes & Diary",
            date_obj=utc_dt,
        )

        assert filepath.endswith("logs/daily/2026-09-08.md")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "- [14:13] 고든의 퇴사 이야기" in content
    finally:
        shutil.rmtree(temp_dir)


def test_timezone_date_rollover_utc_to_kst():
    temp_dir = tempfile.mkdtemp()
    try:
        service = AgentService(base_dir=temp_dir)

        # 2026-09-07 20:00 UTC is 2026-09-08 05:00 KST
        utc_night = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)
        filepath = service.append_or_update_lifelog(
            content="새벽 기상 메모",
            category="Daily Notes & Diary",
            date_obj=utc_night,
        )

        assert filepath.endswith("2026-09-08.md")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "- [05:00] 새벽 기상 메모" in content
    finally:
        shutil.rmtree(temp_dir)


def test_append_to_gtd_inbox_smart_section_routing():
    temp_dir = tempfile.mkdtemp()
    try:
        gtd_dir = os.path.join(temp_dir, "gtd")
        os.makedirs(gtd_dir, exist_ok=True)
        inbox_file = os.path.join(gtd_dir, "inbox.md")
        with open(inbox_file, "w", encoding="utf-8") as f:
            f.write(
                "# 📥 GTD Inbox\n\n"
                "## 🏢 회사 업무 (01_work)\n"
                "- [ ] 기존 업무\n\n"
                "## 🧘 개인 생활 & 건강 (02_personal)\n"
                "- [ ] 기존 개인 일과\n"
            )

        service = AgentService(base_dir=temp_dir)
        service.append_to_gtd_inbox("서산 여행 계획 및 맛집 방문 (용현집, 어죽) 🚗🍲")

        with open(inbox_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Check that the task was inserted under personal section
        personal_idx = next(i for i, l in enumerate(lines) if "개인 생활" in l)
        assert "- [ ] 서산 여행 계획 및 맛집 방문 (용현집, 어죽) 🚗🍲\n" == lines[personal_idx + 1]
    finally:
        shutil.rmtree(temp_dir)


def test_append_lifelog_multiline_and_deduplication():
    temp_dir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(temp_dir, "logs", "daily"), exist_ok=True)
        service = AgentService(base_dir=temp_dir)
        kst = get_app_timezone()
        now = datetime(2026, 9, 9, 9, 19, tzinfo=kst)

        multiline_content = (
            "고든은 내 팀원이라 인수인계는 완료됐어.\n"
            "오늘은 6시에 퇴근해서 와이프랑 영화를 보러 갈거야. 오늘은 문화데이니까."
        )

        # 1. First append
        filepath = service.append_or_update_lifelog(
            content=multiline_content,
            category="Daily Notes & Diary",
            date_obj=now,
        )

        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        # Check multiline was joined into a single clean line
        expected_line = "- [09:19] 고든은 내 팀원이라 인수인계는 완료됐어. 오늘은 6시에 퇴근해서 와이프랑 영화를 보러 갈거야. 오늘은 문화데이니까."
        assert expected_line in text

        # 2. Second append with duplicate content should be ignored
        service.append_or_update_lifelog(
            content=multiline_content,
            category="Daily Notes & Diary",
            date_obj=now,
        )

        with open(filepath, "r", encoding="utf-8") as f:
            text2 = f.read()

        # Count occurrences of the line: must be exactly 1
        assert text2.count(expected_line) == 1
    finally:
        shutil.rmtree(temp_dir)


def test_remove_gtd_tasks():
    temp_dir = tempfile.mkdtemp()
    try:
        gtd_dir = os.path.join(temp_dir, "gtd")
        os.makedirs(gtd_dir, exist_ok=True)
        inbox_file = os.path.join(gtd_dir, "inbox.md")
        next_file = os.path.join(gtd_dir, "next_actions.md")

        with open(inbox_file, "w", encoding="utf-8") as f:
            f.write(
                "# Inbox\n"
                "- [ ] tiara_ad 처리 방안 가이드라인 후속 작업 🚨\n"
                "- [ ] 차주 주간 보고 아젠다 미리 준비 📊\n"
                "- [ ] 서산 여행 계획 🚗\n"
            )

        with open(next_file, "w", encoding="utf-8") as f:
            f.write(
                "# Next Actions\n"
                "- [ ] tiara_ad 처리 방안 가이드라인 후속 작업 🚨\n"
                "- [ ] 가족을 위한 시간 보내기 💌\n"
                "- [ ] 생필품 구매 🛒\n"
            )

        service = AgentService(base_dir=temp_dir)
        user_msg = "tiara_ad는 제거해. 주간보고 아젠다도 제거. 가족위한 시간 보내기 제거"
        removed = service.find_and_remove_matching_tasks(user_msg)

        assert any("tiara_ad" in r for r in removed)
        assert any("주간 보고" in r or "주간보고" in r for r in removed)
        assert any("가족" in r for r in removed)

        with open(inbox_file, "r", encoding="utf-8") as f:
            inbox_text = f.read()
        with open(next_file, "r", encoding="utf-8") as f:
            next_text = f.read()

        assert "tiara_ad" not in inbox_text
        assert "tiara_ad" not in next_text
        assert "가족" not in next_text
        assert "서산 여행 계획" in inbox_text
        assert "생필품 구매" in next_text
    finally:
        shutil.rmtree(temp_dir)


def test_read_daily_log_and_gtd_files():
    temp_dir = tempfile.mkdtemp()
    try:
        daily_dir = os.path.join(temp_dir, "logs", "daily")
        gtd_dir = os.path.join(temp_dir, "gtd")
        os.makedirs(daily_dir, exist_ok=True)
        os.makedirs(gtd_dir, exist_ok=True)

        service = AgentService(base_dir=temp_dir)
        kst = get_app_timezone()
        now = datetime(2026, 9, 10, 10, 0, tzinfo=kst)

        # 1. Empty daily log
        empty_res = service.read_daily_log(now)
        assert "작성된 일일 로그가 아직 없습니다" in empty_res

        # 2. Append and read
        service.append_or_update_lifelog("테스트 일과 기록 작성", "Daily Notes & Diary", date_obj=now)
        log_res = service.read_daily_log(now)
        assert "2026-09-10" in log_res
        assert "테스트 일과 기록 작성" in log_res

        # 3. Create GTD inbox & next_actions
        inbox_file = os.path.join(gtd_dir, "inbox.md")
        next_file = os.path.join(gtd_dir, "next_actions.md")
        with open(inbox_file, "w", encoding="utf-8") as f:
            f.write("# Inbox\n- [ ] 인박스 태스크 1\n- [ ] 인박스 태스크 2\n")
        with open(next_file, "w", encoding="utf-8") as f:
            f.write("# Next Actions\n- [ ] 다음 행동 태스크 1\n- [x] 완료된 태스크\n")

        gtd_res = service.read_gtd_files()
        assert "수집함 Inbox" in gtd_res
        assert "미완료 `2`개" in gtd_res
        assert "다음 행동 Next Actions" in gtd_res
        assert "미완료 `1`개" in gtd_res

        # 4. Composite view
        comp_res = service.read_gtd_and_daily_log(now)
        assert "오늘 일일 로그" in comp_res
        assert "현재 GTD 파일 현황 브리핑" in comp_res
    finally:
        shutil.rmtree(temp_dir)



