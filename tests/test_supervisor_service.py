import os
import shutil
import tempfile

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

def test_supervisor_pipeline_butler_workflow(db_session):
    temp_dir = tempfile.mkdtemp()
    try:
        supervisor = SupervisorService(db=db_session, base_dir=temp_dir)
        session_id = "test_user_session"

        # 1. 단순 잡담 -> chat_only (기록 X, 커밋 X)
        res_chat = supervisor.process_user_request(
            session_id=session_id,
            user_message="안녕하세요! 오늘 날씨 좋네요.",
            channel="web",
            auto_push=False,
        )
        assert res_chat["intent"] == "chat_only"
        assert res_chat["filepath"] is None
        assert res_chat["git_pushed"] is False
        assert res_chat["pending_log"] is None

        # 2. 운동 일과 언급 -> log_suggest (제안 + pending_log 보관, 아직 기록 X)
        res_suggest = supervisor.process_user_request(
            session_id=session_id,
            user_message="오늘 저녁에 한강 러닝 5km 뛰고 왔어!",
            channel="web",
            auto_push=False,
        )
        assert res_suggest["intent"] == "log_suggest"
        assert res_suggest["filepath"] is None
        assert res_suggest["pending_log"] is not None
        assert "러닝 5km" in res_suggest["pending_log"]["content"]
        assert res_suggest["pending_log"]["category"] == "Workout & Health"

        # 3. 제안 승인 -> log_confirm (마크다운 기록 완료, pending_log 클리어)
        res_confirm = supervisor.process_user_request(
            session_id=session_id,
            user_message="응 좋아 기록해줘",
            channel="web",
            auto_push=False,
        )
        assert res_confirm["intent"] == "log_confirm"
        assert res_confirm["filepath"] is not None
        assert res_confirm["pending_log"] is None

        # 4. 직접 명령 -> log_explicit (즉시 마크다운 기록)
        res_explicit = supervisor.process_user_request(
            session_id=session_id,
            user_message="/log 프로젝트 기획서 검토 완료",
            channel="web",
            auto_push=False,
        )
        assert res_explicit["intent"] == "log_explicit"
        assert res_explicit["filepath"] is not None
    finally:
        shutil.rmtree(temp_dir)


def test_supervisor_task_briefing_workflow(db_session):
    temp_dir = tempfile.mkdtemp()
    try:
        import os
        gtd_dir = os.path.join(temp_dir, "gtd")
        os.makedirs(gtd_dir, exist_ok=True)
        with open(os.path.join(gtd_dir, "next_actions.md"), "w", encoding="utf-8") as f:
            f.write("# Next Actions\n- [ ] 중요한 계약서 검토 완료하기\n")

        supervisor = SupervisorService(db=db_session, base_dir=temp_dir)
        res = supervisor.process_user_request(
            session_id="briefing_session",
            user_message="오늘 해야할 일 정리해줘",
            channel="telegram",
            auto_push=False,
        )

        assert res["intent"] == "task_briefing"
        assert res["filepath"] is None
        assert "오늘의 일정 및 GTD 할 일 브리핑" in res["ai_response"]
        assert "중요한 계약서 검토 완료하기" in res["ai_response"]
    finally:
        shutil.rmtree(temp_dir)


def test_supervisor_repo_sync_workflows(db_session):
    temp_dir = tempfile.mkdtemp()
    try:
        import os
        gtd_dir = os.path.join(temp_dir, "gtd")
        os.makedirs(gtd_dir, exist_ok=True)
        with open(os.path.join(gtd_dir, "next_actions.md"), "w", encoding="utf-8") as f:
            f.write("# Next Actions\n- [ ] 새로운 기능 배포 점검\n")

        supervisor = SupervisorService(db=db_session, base_dir=temp_dir)

        # 1. 단독 최신화 요청
        res_sync = supervisor.process_user_request(
            session_id="sync_session",
            user_message="gtd 레포 최신화해줘",
            channel="telegram",
            auto_push=False,
        )
        assert res_sync["intent"] == "repo_sync"
        assert "GTD 저장소 동기화 결과" in res_sync["ai_response"]

        # 2. 최신화 후 브리핑 복합 요청
        res_sync_brief = supervisor.process_user_request(
            session_id="sync_session",
            user_message="gtd 레포 최신화하고 다시 알려줘",
            channel="telegram",
            auto_push=False,
        )
        assert res_sync_brief["intent"] == "repo_sync_and_briefing"
        assert "동기화" in res_sync_brief["ai_response"]
        assert "오늘의 일정 및 GTD 할 일 브리핑" in res_sync_brief["ai_response"]
        assert "새로운 기능 배포 점검" in res_sync_brief["ai_response"]
    finally:
        shutil.rmtree(temp_dir)


def test_supervisor_context_aware_logging_workflow(db_session):
    temp_dir = tempfile.mkdtemp()
    try:
        supervisor = SupervisorService(db=db_session, base_dir=temp_dir)
        session_id = "context_log_session"

        # 1. 일상/감정 사연 대화
        story = "지난 주말에 병원에서 가족 검진 결과를 듣고 왔는데 걱정이 많아. 잘 극복해야지."
        res_story = supervisor.process_user_request(
            session_id=session_id,
            user_message=story,
            channel="telegram",
            auto_push=False,
        )
        assert res_story["intent"] in ["chat_only", "log_suggest"]

        # 2. 맥락 참조 기록 요청 ("오늘 로그에 내가 아까 말한 내용도 기록해줘. 내 감정이니까")
        res_context_log = supervisor.process_user_request(
            session_id=session_id,
            user_message="오늘 로그에 내가 아까 말한 내용도 기록해줘. 내 감정이니까",
            channel="telegram",
            auto_push=False,
        )
        assert res_context_log["intent"] == "log_explicit"
        assert res_context_log["filepath"] is not None
        with open(res_context_log["filepath"], encoding="utf-8") as f:
            assert "가족 검진 결과" in f.read()
    finally:
        shutil.rmtree(temp_dir)


def test_supervisor_repo_push_workflow(db_session):
    temp_dir = tempfile.mkdtemp()
    try:
        supervisor = SupervisorService(db=db_session, base_dir=temp_dir)
        res_push = supervisor.process_user_request(
            session_id="push_session",
            user_message="푸시해줘",
            channel="telegram",
            auto_push=False,
        )
        assert res_push["intent"] == "repo_push"
        assert "GitHub 푸시 결과" in res_push["ai_response"]
    finally:
        shutil.rmtree(temp_dir)


def test_supervisor_pure_directive_logging_workflow(db_session):
    temp_dir = tempfile.mkdtemp()
    try:
        supervisor = SupervisorService(db=db_session, base_dir=temp_dir)
        session_id = "gordon_session"

        # 1. 고든 퇴사 이야기
        supervisor.process_user_request(
            session_id=session_id,
            user_message="오늘은 첫 버디였던 고든이 퇴사하는 날이야. 아쉽고 고마운 마음이 크네.",
            channel="telegram",
            auto_push=False,
        )

        # 2. "응 오늘 로그에 기록해줘" 지시
        res = supervisor.process_user_request(
            session_id=session_id,
            user_message="응 오늘 로그에 기록해줘",
            channel="telegram",
            auto_push=False,
        )
        assert res["intent"] == "log_explicit"
        assert res["filepath"] is not None
        with open(res["filepath"], encoding="utf-8") as f:
            content = f.read()
            assert "고든이 퇴사하는 날" in content
            assert "응 오늘 로그에" not in content
    finally:
        shutil.rmtree(temp_dir)


def test_supervisor_dual_logging_workflow(db_session):
    temp_dir = tempfile.mkdtemp()
    try:
        # Create inbox and logs/daily structure
        gtd_dir = os.path.join(temp_dir, "gtd")
        daily_dir = os.path.join(temp_dir, "logs", "daily")
        os.makedirs(gtd_dir, exist_ok=True)
        os.makedirs(daily_dir, exist_ok=True)

        inbox_file = os.path.join(gtd_dir, "inbox.md")
        with open(inbox_file, "w", encoding="utf-8") as f:
            f.write(
                "# 📥 GTD Inbox\n\n"
                "## 🏢 회사 업무 (01_work)\n\n"
                "## 🧘 개인 생활 & 건강 (02_personal)\n"
            )

        supervisor = SupervisorService(db=db_session, base_dir=temp_dir)
        session_id = "dual_log_session"

        prompt = (
            "회사에서 리조트를 신청할 수 있거든? 와이프와 가려고 부여리조트를 신청했는데 떨어졌어. "
            "그래서 그냥 서산쪽으로 여행을 가보려구. 용현집이라고 어죽을 파는 곳을 좋아했거든? "
            "그래서 거기를 가보고싶고, 또간집에 나온 게국지 집에도 가보고싶대. 로그와 gtd에 기록해줘."
        )

        res = supervisor.process_user_request(
            session_id=session_id,
            user_message=prompt,
            channel="telegram",
            auto_push=False,
        )

        assert res["intent"] == "log_dual"
        assert res["filepath"] is not None

        # Verify daily log
        with open(res["filepath"], encoding="utf-8") as f:
            daily_content = f.read()
            assert "서산쪽으로 여행" in daily_content
            assert "로그와 gtd에" not in daily_content

        # Verify GTD inbox
        with open(inbox_file, encoding="utf-8") as f:
            inbox_content = f.read()
            assert "서산" in inbox_content
            assert "여행" in inbox_content
            assert "용현집" in inbox_content
    finally:
        shutil.rmtree(temp_dir)





