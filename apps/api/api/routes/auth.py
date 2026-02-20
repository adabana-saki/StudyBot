"""認証ルート"""

import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from api.auth.discord_oauth import exchange_code, get_user_info
from api.auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from api.config import settings
from api.database import get_pool
from api.models.schemas import AuthCodeExchangeRequest, RefreshRequest, TokenResponse
from api.services.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

AUTH_CODE_TTL = 60  # 認証コードの有効期限（秒）
AUTH_CODE_PREFIX = "auth_code:"


@router.get("/discord")
async def discord_login():
    """Discord OAuth2 ログインURLにリダイレクト"""
    params = (
        f"client_id={settings.DISCORD_CLIENT_ID}"
        f"&redirect_uri={settings.DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
    )
    return RedirectResponse(f"https://discord.com/api/oauth2/authorize?{params}")


@router.get("/callback")
async def discord_callback(code: str = Query(...)):
    """Discord OAuth2 コールバック"""
    # コードをトークンに交換
    token_data = await exchange_code(code)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="認証に失敗しました")

    access_token = token_data["access_token"]

    # ユーザー情報を取得
    user_info = await get_user_info(access_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ユーザー情報の取得に失敗しました"
        )

    user_id = int(user_info["id"])
    username = user_info.get("username", "")

    # Discord アバターURL を構築
    discord_avatar = user_info.get("avatar")
    avatar_url = ""
    if discord_avatar:
        ext = "gif" if discord_avatar.startswith("a_") else "png"
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{discord_avatar}.{ext}?size=128"

    # DB にユーザーを確保
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username, avatar_url)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE SET username = $2, avatar_url = $3
            """,
            user_id,
            username,
            avatar_url,
        )

    # JWT生成
    jwt_access = create_access_token(user_id, username)
    jwt_refresh = create_refresh_token(user_id)

    # 短命の認証コードをRedisに保存（JWTをURLに露出させない）
    auth_code = str(uuid.uuid4())
    redis = get_redis()
    await redis.set(
        f"{AUTH_CODE_PREFIX}{auth_code}",
        f"{jwt_access}\n{jwt_refresh}",
        ex=AUTH_CODE_TTL,
    )

    # WebUIにリダイレクト（認証コードのみ）
    redirect_url = f"{settings.WEB_BASE_URL}/auth/callback?code={auth_code}"
    return RedirectResponse(redirect_url)


@router.post("/exchange", response_model=TokenResponse)
async def exchange_auth_code(request: AuthCodeExchangeRequest):
    """認証コードをJWTトークンに交換"""
    redis = get_redis()
    key = f"{AUTH_CODE_PREFIX}{request.code}"
    stored = await redis.get(key)

    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="認証コードが無効か有効期限切れです",
        )

    # 使い捨て: 即座に削除
    await redis.delete(key)

    parts = stored.split("\n", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="認証データが不正です",
        )

    return TokenResponse(access_token=parts[0], refresh_token=parts[1])


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """トークンをリフレッシュ"""
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="無効なリフレッシュトークンです"
        )

    user_id = int(payload["sub"])

    # ユーザー名を取得
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT username FROM users WHERE user_id = $1", user_id)

    username = row["username"] if row else ""

    new_access = create_access_token(user_id, username)
    new_refresh = create_refresh_token(user_id)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)
