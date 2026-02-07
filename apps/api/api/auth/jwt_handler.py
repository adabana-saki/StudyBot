"""JWT認証ハンドラー"""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from api.config import settings


def create_access_token(user_id: int, username: str) -> str:
    """アクセストークンを生成"""
    expire = datetime.now(UTC) + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.API_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """リフレッシュトークンを生成"""
    expire = datetime.now(UTC) + timedelta(days=30)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.API_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """トークンをデコード"""
    try:
        payload = jwt.decode(token, settings.API_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
