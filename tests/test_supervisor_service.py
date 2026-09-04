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
