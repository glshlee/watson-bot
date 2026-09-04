from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """DB 테이블 생성 및 필요 컬럼 자동 마이그레이션을 수행합니다."""
    Base.metadata.create_all(bind=engine)
    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA table_info(sessions)")
            columns = [row[1] for row in result.fetchall()]
            if columns and "pending_log" not in columns:
                conn.exec_driver_sql("ALTER TABLE sessions ADD COLUMN pending_log TEXT")

