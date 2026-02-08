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
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
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


def validate_settings() -> list[str]:
    """必須設定のバリデーション（起動時チェック用）"""
    warnings = []
    if not settings.DATABASE_URL:
        warnings.append("DATABASE_URL が未設定です")
    if settings.API_SECRET_KEY == "change-me-in-production":
        warnings.append("API_SECRET_KEY がデフォルト値です。本番環境では変更してください")
    if not settings.DISCORD_CLIENT_ID:
        warnings.append("DISCORD_CLIENT_ID が未設定です（OAuth認証が無効）")
    if not settings.DISCORD_CLIENT_SECRET:
        warnings.append("DISCORD_CLIENT_SECRET が未設定です（OAuth認証が無効）")
    return warnings
