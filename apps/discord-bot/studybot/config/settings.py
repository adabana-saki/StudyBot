import os
from pathlib import Path

from dotenv import load_dotenv


class Settings:
    """アプリケーション設定（環境変数から読み込み）"""

    def __init__(self):
        env_path = Path(__file__).parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

        # Discord
        self.DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
        self.BOT_OWNER_ID: int | None = int(os.getenv("BOT_OWNER_ID", "0")) or None

        # Database
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")
        self.DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
        self.DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "5"))
        self.DB_COMMAND_TIMEOUT: int = int(os.getenv("DB_COMMAND_TIMEOUT", "30"))

        # OpenAI
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.OPENAI_MODEL_HEAVY: str = os.getenv(
            "OPENAI_MODEL_HEAVY", "gpt-4o"
        )
        self.AI_DAILY_LIMIT: int = int(os.getenv("AI_DAILY_LIMIT", "10"))

        # API / Web (Phase 2)
        self.API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "change-me-in-production")
        self.DISCORD_CLIENT_ID: str = os.getenv("DISCORD_CLIENT_ID", "")
        self.DISCORD_CLIENT_SECRET: str = os.getenv("DISCORD_CLIENT_SECRET", "")
        self.API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.WEB_BASE_URL: str = os.getenv("WEB_BASE_URL", "http://localhost:3000")

        # Redis
        self.REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def database_url_fixed(self) -> str | None:
        """PostgreSQL URLの正規化"""
        if not self.DATABASE_URL:
            return None
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self.DATABASE_URL


settings = Settings()
