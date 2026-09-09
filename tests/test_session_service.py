import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.services.session_service import SessionService


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

def test_session_creation_and_history(db_session):
    service = SessionService(db_session)
    session_id = "test_user_001"

    # Add messages
    service.add_message(session_id, role="user", content="Hello, Watson!")
    service.add_message(session_id, role="assistant", content="Hello! How can I help you today?")

    # Retrieve history
    history = service.get_session_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello, Watson!"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hello! How can I help you today?"


def test_session_management_lifecycle(db_session):
    service = SessionService(db_session)
    session_id = "test_lifecycle_session"

    # 1. Create session and verify default title
    session = service.get_or_create_session(session_id, channel="web", title="New Conversation")
    assert session.title == "New Conversation"

    # 2. Auto-update title on first message
    service.auto_update_session_title(session_id, "오늘 저녁 한강 러닝 5km 완료")
    updated_session = service.get_session(session_id)
    assert updated_session is not None
    assert "오늘 저녁 한강 러닝" in updated_session.title

    # 3. Explicitly update title
    renamed = service.update_session_title(session_id, "러닝 기록 세션")
    assert renamed is not None
    assert renamed.title == "러닝 기록 세션"

    # 4. Add messages and verify metadata
    service.add_message(session_id, "user", "러닝 5km 완주했습니다.")
    service.add_message(session_id, "assistant", "수고하셨습니다!")
    sessions_meta = service.list_sessions()
    target = next((s for s in sessions_meta if s["id"] == session_id), None)
    assert target is not None
    assert target["message_count"] == 2
    assert "수고하셨습니다!" in target["last_message"]

    # 5. Clear messages
    cleared = service.clear_session_messages(session_id)
    assert cleared is True
    history_after_clear = service.get_session_history(session_id)
    assert len(history_after_clear) == 0
    assert service.get_session(session_id) is not None  # Session itself still exists

    # 6. Delete session
    deleted = service.delete_session(session_id)
    assert deleted is True
    assert service.get_session(session_id) is None

