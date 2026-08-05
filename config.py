import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Life log repository path
DEFAULT_LIFE_LOG_PATH = str(Path(__file__).resolve().parent.parent / "life_log")
LIFE_LOG_PATH = os.getenv("LIFE_LOG_PATH", DEFAULT_LIFE_LOG_PATH)
