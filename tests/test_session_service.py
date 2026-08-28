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
