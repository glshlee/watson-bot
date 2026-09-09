from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Watson GitHub LifeLog Agent"
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # Git & GTD Storage Configuration
    REPO_PATH: str = "."
    GTD_PATH: str = ""  # Dedicated external GTD/lifelog directory (ADR-007)
    GIT_REMOTE_NAME: str = "origin"
    GIT_BRANCH: str = "main"
    
    # Timezone Configuration (ADR-013)
    TIMEZONE: str = "Asia/Seoul"
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_CHAT_IDS: str = ""  # Comma separated
    
    # LLM Configuration (Gemini / OpenAI / Custom)
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-flash"

    # Web Authentication & Cloudflare Tunnel (ADR-015)
    WEB_AUTH_ENABLED: bool = False
    WEB_AUTH_USERNAME: str = "watson"
    WEB_AUTH_PASSWORD: str = ""
    CLOUDFLARE_TUNNEL_TOKEN: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()


def get_app_timezone() -> ZoneInfo:
    """애플리케이션에 설정된 타임존 객체를 반환합니다 (기본값: Asia/Seoul)."""
    try:
        return ZoneInfo(settings.TIMEZONE)
    except Exception:  # noqa: BLE001
        return ZoneInfo("Asia/Seoul")


def get_now(tz: ZoneInfo | None = None) -> datetime:
    """애플리케이션 설정 타임존(기본값: Asia/Seoul, KST) 기준 현재 datetime을 반환합니다."""
    return datetime.now(tz or get_app_timezone())

