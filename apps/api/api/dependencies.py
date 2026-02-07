"""FastAPI 依存性注入"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth.jwt_handler import decode_token
from api.database import get_pool

security = HTTPBearer()


async def get_db():
    """DB接続プールを取得"""
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """現在のユーザーを取得"""
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
        )

    user_id = int(payload["sub"])
    username = payload.get("username", "")
    return {"user_id": user_id, "username": username}
