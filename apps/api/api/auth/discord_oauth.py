"""Discord OAuth2 認証"""

import logging

import httpx

from api.config import settings

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2"


def get_oauth_url(state: str = "") -> str:
    """Discord OAuth2 認証URLを生成"""
    params = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "redirect_uri": settings.DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
    }
    if state:
        params["state"] = state
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{DISCORD_OAUTH_URL}/authorize?{query}"


async def exchange_code(code: str) -> dict | None:
    """認証コードをトークンに交換"""
    data = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "client_secret": settings.DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.DISCORD_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{DISCORD_OAUTH_URL}/token", data=data)
        if resp.status_code != 200:
            logger.error(f"Discord OAuth token交換失敗: {resp.status_code} {resp.text}")
            return None
        return resp.json()


async def get_user_info(access_token: str) -> dict | None:
    """Discordユーザー情報を取得"""
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
        if resp.status_code != 200:
            logger.error(f"Discord ユーザー情報取得失敗: {resp.status_code}")
            return None
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict | None:
    """リフレッシュトークンでアクセストークンを更新"""
    data = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "client_secret": settings.DISCORD_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{DISCORD_OAUTH_URL}/token", data=data)
        if resp.status_code != 200:
            logger.error(f"Discord トークンリフレッシュ失敗: {resp.status_code}")
            return None
        return resp.json()
