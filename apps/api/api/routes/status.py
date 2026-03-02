"""システムステータス確認エンドポイント"""

import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import ComponentStatus, SystemStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/status", tags=["status"])

APP_VERSION = "2.0.0"


async def _check_postgres() -> ComponentStatus:
    """PostgreSQL接続チェック"""
    try:
        pool = get_pool()
        start = time.monotonic()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(name="PostgreSQL", status="ok", latency_ms=round(latency, 1))
    except Exception as e:
        logger.warning("PostgreSQL health check failed: %s", e)
        return ComponentStatus(name="PostgreSQL", status="down", details={"error": str(e)})


async def _check_redis() -> ComponentStatus:
    """Redis接続チェック"""
    try:
        from api.services.redis_client import get_redis

        r = get_redis()
        start = time.monotonic()
        await r.ping()
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(name="Redis", status="ok", latency_ms=round(latency, 1))
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return ComponentStatus(name="Redis", status="down", details={"error": str(e)})


async def _check_discord_bot() -> ComponentStatus:
    """Discord Botハートビートチェック (Redis key: bot:heartbeat)"""
    try:
        from api.services.redis_client import get_redis

        r = get_redis()
        raw = await r.get("bot:heartbeat")
        if not raw:
            return ComponentStatus(
                name="Discord Bot", status="down", details={"error": "ハートビートなし"}
            )

        data = json.loads(raw)
        return ComponentStatus(
            name="Discord Bot",
            status="ok",
            latency_ms=data.get("ws_latency_ms"),
            details={
                "bot_name": data.get("bot_name", ""),
                "guild_count": data.get("guild_count", 0),
                "updated_at": data.get("updated_at", ""),
            },
        )
    except RuntimeError:
        # Redis未初期化
        return ComponentStatus(name="Discord Bot", status="down", details={"error": "Redis未接続"})
    except Exception as e:
        logger.warning("Discord Bot health check failed: %s", e)
        return ComponentStatus(name="Discord Bot", status="down", details={"error": str(e)})


def _check_firebase() -> ComponentStatus:
    """Firebase初期化チェック"""
    try:
        from api.services.push_service import get_push_service

        svc = get_push_service()
        if svc._initialized:
            return ComponentStatus(name="Firebase", status="ok")
        return ComponentStatus(name="Firebase", status="degraded", details={"error": "未初期化"})
    except RuntimeError:
        return ComponentStatus(name="Firebase", status="down", details={"error": "サービス未起動"})


@router.get("", response_model=SystemStatusResponse)
async def get_system_status():
    """システム全体のステータスを返す（認証不要）"""
    components = [
        await _check_postgres(),
        await _check_redis(),
        await _check_discord_bot(),
        _check_firebase(),
    ]

    has_down = any(c.status == "down" for c in components)
    overall = "degraded" if has_down else "ok"

    return SystemStatusResponse(
        status=overall,
        version=APP_VERSION,
        components=components,
        checked_at=datetime.now(timezone.utc),
    )


@router.post("/ping")
async def test_push_notification(
    current_user: dict = Depends(get_current_user),
):
    """テストプッシュ通知を送信（認証必要）"""
    try:
        from api.services.push_service import get_push_service

        svc = get_push_service()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="プッシュ通知サービスが未初期化です",
        )

    if not svc._initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase未初期化（認証情報を確認してください）",
        )

    user_id = current_user["user_id"]
    sent = await svc.send_to_user(
        user_id=user_id,
        title="StudyBot テスト通知",
        body="プッシュ通知が正常に動作しています！",
        notification_type="test",
    )

    if sent == 0:
        return {"sent": 0, "message": "登録デバイスがありません"}

    return {"sent": sent, "message": f"{sent}件のデバイスに送信しました"}
