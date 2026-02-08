"""モバイル用OAuth認証ルート"""

import logging

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from api.auth.discord_oauth import exchange_code, get_user_info
from api.auth.jwt_handler import create_access_token, create_refresh_token
from api.config import settings
from api.database import get_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth/discord", tags=["mobile-auth"])


@router.get("/login")
async def mobile_login(redirect_uri: str = Query(...)):
    """モバイル用 Discord OAuth2 ログイン"""
    params = (
        f"client_id={settings.DISCORD_CLIENT_ID}"
        f"&redirect_uri={settings.DISCORD_REDIRECT_URI.replace('/callback', '/mobile-callback')}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
        f"&state={redirect_uri}"
    )
    return RedirectResponse(f"https://discord.com/api/oauth2/authorize?{params}")


@router.get("/mobile-callback")
async def mobile_callback(
    code: str = Query(...),
    state: str = Query(""),
):
    """モバイル用 Discord OAuth2 コールバック"""
    mobile_redirect_uri = settings.DISCORD_REDIRECT_URI.replace("/callback", "/mobile-callback")
    token_data = await exchange_code(code, redirect_uri=mobile_redirect_uri)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="認証に失敗しました")

    access_token = token_data["access_token"]
    user_info = await get_user_info(access_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ユーザー情報の取得に失敗しました"
        )

    user_id = int(user_info["id"])
    username = user_info.get("username", "")

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET username = $2
            """,
            user_id,
            username,
        )

    jwt_access = create_access_token(user_id, username)
    jwt_refresh = create_refresh_token(user_id)

    # deep link redirect
    redirect_url = state or settings.WEB_BASE_URL
    separator = "&" if "?" in redirect_url else "?"
    return RedirectResponse(f"{redirect_url}{separator}token={jwt_access}&refresh={jwt_refresh}")
