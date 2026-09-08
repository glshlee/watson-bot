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

