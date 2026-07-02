import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    DISABLE_SSL_VERIFY: bool = os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true"
    REQUESTS_CA_BUNDLE: str = os.getenv("REQUESTS_CA_BUNDLE", "")
    HTTPS_PROXY: str = os.getenv("HTTPS_PROXY", "")
    GMAIL_USER: str = os.getenv("GMAIL_USER", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    USE_TEAMS: bool = os.getenv("USE_TEAMS", "false").lower() == "true"
    GRAPH_TOKEN: str = os.getenv("GRAPH_TOKEN", "")
    DB_PATH: str = os.path.join(os.path.dirname(__file__), "..", "rto.db")

settings = Settings()
