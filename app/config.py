from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Watson GitHub LifeLog Agent"
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # Git Configuration
    REPO_PATH: str = "."
    GIT_REMOTE_NAME: str = "origin"
    GIT_BRANCH: str = "main"
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_CHAT_IDS: str = ""  # Comma separated
    
    # LLM Configuration (Gemini / OpenAI / Custom)
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-flash"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
