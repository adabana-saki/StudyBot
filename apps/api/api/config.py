"""API設定"""

import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """API設定"""

    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "change-me-in-production")
    DISCORD_CLIENT_ID: str = os.getenv("DISCORD_CLIENT_ID", "")
    DISCORD_CLIENT_SECRET: str = os.getenv("DISCORD_CLIENT_SECRET", "")
    DISCORD_REDIRECT_URI: str = os.getenv(
        "DISCORD_REDIRECT_URI", "http://localhost:8000/api/auth/callback"
    )
    WEB_BASE_URL: str = os.getenv("WEB_BASE_URL", "http://localhost:3000")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    @property
    def database_url_fixed(self) -> str | None:
        if not self.DATABASE_URL:
            return None
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self.DATABASE_URL


settings = Settings()
