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

def test_supervisor_pipeline(db_session):
    temp_dir = tempfile.mkdtemp()
    try:
        supervisor = SupervisorService(db=db_session, base_dir=temp_dir)
        res = supervisor.process_user_request(
            session_id="telegram:12345",
            user_message="Ran 5km at evening",
            category="Workout & Health",
            channel="telegram",
            auto_push=False
        )

        assert res["session_id"] == "telegram:12345"
        assert os.path.exists(res["filepath"])
        assert "왓슨" in res["ai_response"]
    finally:
        shutil.rmtree(temp_dir)
