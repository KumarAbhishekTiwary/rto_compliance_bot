"""Central configuration loaded from .env"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Slack
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")

    # SMTP / Gmail
    GMAIL_USER: str = os.getenv("GMAIL_USER", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")

    # DB
    DB_PATH: str = os.getenv("DB_PATH", "rto.db")
    DB_URL: str = f"sqlite:///{DB_PATH}"

    # App
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    SLA_HOURS: int = int(os.getenv("SLA_HOURS", "24"))
    SLA_MINUTES: int = int(os.getenv("SLA_MINUTES", "2"))  # 0 = use SLA_HOURS
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
