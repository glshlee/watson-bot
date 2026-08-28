import os
import shutil
import tempfile
from datetime import datetime, timezone

from app.services.agent_service import AgentService


def test_append_or_update_lifelog():
    temp_dir = tempfile.mkdtemp()
    try:
        service = AgentService(base_dir=temp_dir)
        now = datetime(2026, 8, 28, 14, 30, tzinfo=timezone.utc)

        filepath = service.append_or_update_lifelog(
            content="Today I completed Phase 2 architecture for Watson.",
            category="Daily Notes & Diary",
            date_obj=now
        )

        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# 📅 Life Log - 2026-08-28" in content
        assert "## 📝 Daily Notes & Diary" in content
        assert "- [14:30] Today I completed Phase 2 architecture for Watson." in content
    finally:
        shutil.rmtree(temp_dir)
