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
    GMAIL_IMAP_ENABLED: bool = os.getenv("GMAIL_IMAP_ENABLED", "true").lower() in ("1", "true", "yes")

    # DB
    DB_PATH: str = os.getenv("DB_PATH", "rto.db")
    DB_URL: str = f"sqlite:///{DB_PATH}"

    # App
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    SLA_HOURS: int = int(os.getenv("SLA_HOURS", "24"))
    SLA_MINUTES: int = int(os.getenv("SLA_MINUTES", "0"))  # Test/demo override; 0 = use SLA_HOURS
    TEAMS_REMINDER_HOURS: int = int(os.getenv("TEAMS_REMINDER_HOURS", os.getenv("SLA_HOURS", "24")))
    TEAMS_REMINDER_MINUTES: int = int(os.getenv("TEAMS_REMINDER_MINUTES", os.getenv("SLA_MINUTES", "0")))
    EMAIL_REMINDER_HOURS: int = int(os.getenv("EMAIL_REMINDER_HOURS", os.getenv("SLA_HOURS", "24")))
    EMAIL_REMINDER_MINUTES: int = int(os.getenv("EMAIL_REMINDER_MINUTES", os.getenv("SLA_MINUTES", "0")))
    EMAIL_POLL_SECONDS: int = int(os.getenv("EMAIL_POLL_SECONDS", "30"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def _interval_label(self, minutes: int, hours: int) -> str:
        if minutes > 0:
            unit = "minute" if minutes == 1 else "minutes"
            return f"{minutes} {unit}"
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit}"

    def teams_reminder_label(self) -> str:
        return self._interval_label(self.TEAMS_REMINDER_MINUTES, self.TEAMS_REMINDER_HOURS)

    def email_reminder_label(self) -> str:
        return self._interval_label(self.EMAIL_REMINDER_MINUTES, self.EMAIL_REMINDER_HOURS)

settings = Settings()
