import os
import shutil
import tempfile
from unittest.mock import patch

import git
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.services.supervisor_service import SupervisorService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_supervisor_natural_language_delegated_and_slash_log(db_session):
    """ADR-066: 자연어는 파이썬 인텐트 분류 없이 100% LLM(chat_only)으로 위임되고, /log 슬래시 명령어는 즉시 로컬 마크다운에 기록됨을 검증."""
    temp_dir = tempfile.mkdtemp()
    try:
        supervisor = SupervisorService(db=db_session, base_dir=temp_dir, fast_mode=True)
        session_id = "test_user_session"

        # 1. 자연어 대화 -> 인텐트 분류 없이 chat_only
        res_chat = supervisor.process_user_request(
            session_id=session_id,
            user_message="안녕하세요! 오늘 날씨 좋네요.",
            channel="web",
            auto_push=False,
        )
        assert res_chat["intent"] == "chat_only"
        assert res_chat["filepath"] is None
        assert res_chat["git_pushed"] is False

        # 2. 명시적 /log 명령 -> log_explicit (즉시 로컬 마크다운 기록)
        res_explicit = supervisor.process_user_request(
            session_id=session_id,
            user_message="/log 프로젝트 기획서 검토 완료",
            channel="web",
            auto_push=False,
        )
        assert res_explicit["intent"] == "log_explicit"
        assert res_explicit["filepath"] is not None
        assert os.path.exists(res_explicit["filepath"])
    finally:
        shutil.rmtree(temp_dir)


def test_supervisor_autonomous_llm_file_edit_detection(db_session):
    """ADR-066: LLM(AGY 에이전트)이 자연어 요청('은퇴 계획 일정을 someday로 이동시켜줘')을 받아 직접 마크다운 파일을 수정하면, 파이썬이 인텐트 분류 없이도 git status로 변경 파일을 정확히 감지하는지 검증."""
    temp_dir = tempfile.mkdtemp()
    try:
        repo = git.Repo.init(temp_dir)
        gtd_dir = os.path.join(temp_dir, "gtd")
        os.makedirs(gtd_dir, exist_ok=True)
        inbox_file = os.path.join(gtd_dir, "inbox.md")
        someday_file = os.path.join(gtd_dir, "someday_maybe.md")

        with open(inbox_file, "w", encoding="utf-8") as f:
            f.write("# 📥 Inbox\n- [ ] 은퇴 계획 정리 및 독서 📖\n- [ ] 트래블월렛 고객확인 💳\n")
        with open(someday_file, "w", encoding="utf-8") as f:
            f.write("# 💡 GTD Someday / Maybe\n\n## 🎯 개인 목표\n")
        repo.git.add(A=True)
        repo.index.commit("chore: initial gtd files")

        supervisor = SupervisorService(db=db_session, base_dir=temp_dir, fast_mode=False)

        # AGY 에이전트가 직접 inbox.md에서 잘라내어 someday_maybe.md에 붙여넣는 자율 동작 시뮬레이션
        def fake_autonomous_agy(prompt: str, history=None) -> str:
            with open(inbox_file, "w", encoding="utf-8") as f:
                f.write("# 📥 Inbox\n- [ ] 트래블월렛 고객확인 💳\n")
            with open(someday_file, "a", encoding="utf-8") as f:
                f.write("- [ ] 은퇴 계획 정리 및 독서 📖\n")
            return "요청하신 '은퇴 계획 정리 및 독서' 일정을 `gtd/someday_maybe.md`로 이동했습니다!"

        with patch.object(supervisor.llm_provider, "_call_ai_engine", side_effect=fake_autonomous_agy):
            res = supervisor.process_user_request(
                session_id="autonomous_sess",
                user_message="은퇴 계획 일정을 someday로 이동시켜줘",
                channel="web",
            )

        assert res["intent"] == "chat_only"
        assert res["filepath"] is not None
        assert "someday_maybe.md" in res["ai_response"]
        assert len(supervisor.git_service.get_dirty_files()) == 2
    finally:
        shutil.rmtree(temp_dir)


def test_supervisor_slash_shortcuts_and_git_workflows(db_session):
    """ADR-061 & ADR-064: 슬래시(/) 명령어(/today, /gtd, /briefing, /sync, /commit, /push, /status) 워크플로우 검증."""
    temp_dir = tempfile.mkdtemp()
    try:
        repo = git.Repo.init(temp_dir)
        daily_dir = os.path.join(temp_dir, "logs", "daily")
        gtd_dir = os.path.join(temp_dir, "gtd")
        os.makedirs(daily_dir, exist_ok=True)
        os.makedirs(gtd_dir, exist_ok=True)

        inbox_file = os.path.join(gtd_dir, "inbox.md")
        with open(inbox_file, "w", encoding="utf-8") as f:
            f.write("# Inbox\n- [ ] 긴급 버그 수정\n")
        repo.git.add(A=True)
        repo.index.commit("chore: init")

        supervisor = SupervisorService(db=db_session, base_dir=temp_dir, fast_mode=True)

        # 1. /today
        res_today = supervisor.process_user_request(session_id="s1", user_message="/today")
        assert res_today["intent"] == "daily_log_inspect"

        # 2. /gtd
        res_gtd = supervisor.process_user_request(session_id="s1", user_message="/gtd")
        assert res_gtd["intent"] == "gtd_inspect"
        assert "긴급 버그 수정" in res_gtd["ai_response"]

        # 3. /briefing
        res_brief = supervisor.process_user_request(session_id="s1", user_message="/briefing")
        assert res_brief["intent"] == "task_briefing"

        # 4. /sync
        res_sync = supervisor.process_user_request(session_id="s1", user_message="/sync")
        assert res_sync["intent"] == "repo_sync"

        # 5. /log 2회 후 /commit 일괄 커밋 (ADR-064)
        supervisor.process_user_request(session_id="s1", user_message="/log 아침 스트레칭 완료")
        supervisor.agent_service.append_to_gtd_inbox("트래블월렛 고객확인 💳")
        assert len(supervisor.git_service.get_dirty_files()) == 2

        res_commit = supervisor.process_user_request(session_id="s1", user_message="/commit")
        assert res_commit["intent"] == "repo_commit"
        assert "2개 파일" in res_commit["ai_response"]
        assert supervisor.git_service.get_dirty_files() == []

        # 6. /status
        res_status = supervisor.process_user_request(session_id="s1", user_message="/status")
        assert res_status["intent"] == "log_status_inspect"
        assert "정상 기록되어 있습니다" in res_status["ai_response"]
    finally:
        shutil.rmtree(temp_dir)
