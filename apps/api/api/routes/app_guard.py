"""AppGuard: アプリ使用時間トラッキング & ブロック管理ルート"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import (
    AppBreachEventResponse,
    AppBreachSyncRequest,
    AppGuardSummary,
    AppUsageLogResponse,
    AppUsageSyncRequest,
    BlockedAppRequest,
    BlockedAppResponse,
    PaginatedResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/focus/app-guard", tags=["app-guard"])


@router.post("/usage/sync", status_code=status.HTTP_201_CREATED)
async def sync_usage(
    data: AppUsageSyncRequest,
    current_user: dict = Depends(get_current_user),
):
    """デバイスからアプリ使用データを一括アップロード"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        count = 0
        for entry in data.entries:
            await conn.execute(
                """
                INSERT INTO app_usage_logs
                    (user_id, session_id, package_name, app_name,
                     foreground_time_ms, period_start, period_end)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id,
                data.session_id,
                entry.package_name,
                entry.app_name,
                entry.foreground_time_ms,
                entry.period_start,
                entry.period_end,
            )
            count += 1

    return {"synced": count}


@router.get("/usage", response_model=PaginatedResponse[AppUsageLogResponse])
async def get_usage(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """アプリ使用履歴取得（ページネーション）"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM app_usage_logs WHERE user_id = $1",
            user_id,
        )
        rows = await conn.fetch(
            """
            SELECT * FROM app_usage_logs
            WHERE user_id = $1
            ORDER BY period_start DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/usage/session/{session_id}")
async def get_session_usage(
    session_id: int = Path(ge=1),
    current_user: dict = Depends(get_current_user),
):
    """特定セッションのアプリ使用データ"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM app_usage_logs
            WHERE user_id = $1 AND session_id = $2
            ORDER BY foreground_time_ms DESC
            """,
            user_id,
            session_id,
        )

    return [dict(r) for r in rows]


@router.post("/breaches/sync", status_code=status.HTTP_201_CREATED)
async def sync_breaches(
    data: AppBreachSyncRequest,
    current_user: dict = Depends(get_current_user),
):
    """ブリーチイベントを一括アップロード"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        count = 0
        for breach in data.breaches:
            await conn.execute(
                """
                INSERT INTO app_breach_events
                    (user_id, session_id, package_name, app_name,
                     breach_duration_ms, occurred_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_id,
                data.session_id,
                breach.package_name,
                breach.app_name,
                breach.breach_duration_ms,
                breach.occurred_at,
            )
            count += 1

    return {"synced": count}


@router.get("/breaches", response_model=PaginatedResponse[AppBreachEventResponse])
async def get_breaches(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """ブリーチ履歴取得（ページネーション）"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM app_breach_events WHERE user_id = $1",
            user_id,
        )
        rows = await conn.fetch(
            """
            SELECT * FROM app_breach_events
            WHERE user_id = $1
            ORDER BY occurred_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/blocked-apps", response_model=list[BlockedAppResponse])
async def get_blocked_apps(
    current_user: dict = Depends(get_current_user),
):
    """ブロックアプリ一覧"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM blocked_app_lists
            WHERE user_id = $1
            ORDER BY added_at DESC
            """,
            user_id,
        )

    return [dict(r) for r in rows]


@router.post(
    "/blocked-apps",
    response_model=BlockedAppResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_blocked_app(
    data: BlockedAppRequest,
    current_user: dict = Depends(get_current_user),
):
    """ブロックアプリ追加"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO blocked_app_lists (user_id, package_name, app_name, category)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, package_name) DO UPDATE
                SET app_name = EXCLUDED.app_name,
                    category = EXCLUDED.category
            RETURNING *
            """,
            user_id,
            data.package_name,
            data.app_name,
            data.category,
        )

    return dict(row)


@router.delete("/blocked-apps/{package_name:path}")
async def remove_blocked_app(
    package_name: str,
    current_user: dict = Depends(get_current_user),
):
    """ブロックアプリ削除"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM blocked_app_lists
            WHERE user_id = $1 AND package_name = $2
            """,
            user_id,
            package_name,
        )

    if result == "DELETE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定のアプリはブロックリストに存在しません",
        )

    return {"deleted": package_name}


@router.get("/summary", response_model=AppGuardSummary)
async def get_summary(
    current_user: dict = Depends(get_current_user),
    days: int = Query(default=7, ge=1, le=90),
):
    """ダッシュボード用サマリー"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=days)

        # 合計使用時間
        total_usage = await conn.fetchval(
            """
            SELECT COALESCE(SUM(foreground_time_ms), 0)
            FROM app_usage_logs
            WHERE user_id = $1 AND period_start >= $2
            """,
            user_id,
            cutoff,
        )

        # TOP 5 アプリ
        top_apps_rows = await conn.fetch(
            """
            SELECT package_name, app_name,
                   SUM(foreground_time_ms) AS total_ms
            FROM app_usage_logs
            WHERE user_id = $1 AND period_start >= $2
            GROUP BY package_name, app_name
            ORDER BY total_ms DESC
            LIMIT 5
            """,
            user_id,
            cutoff,
        )

        # ブリーチ数
        breach_stats = await conn.fetchrow(
            """
            SELECT COUNT(*) AS count,
                   COALESCE(SUM(breach_duration_ms), 0) AS total_ms
            FROM app_breach_events
            WHERE user_id = $1 AND occurred_at >= $2
            """,
            user_id,
            cutoff,
        )

        # ブロックアプリ数
        blocked_count = await conn.fetchval(
            "SELECT COUNT(*) FROM blocked_app_lists WHERE user_id = $1",
            user_id,
        )

        # ネイティブブロックモード
        mode_row = await conn.fetchrow(
            """
            SELECT native_block_mode FROM user_lock_settings
            WHERE user_id = $1
            """,
            user_id,
        )
        native_mode = mode_row["native_block_mode"] if mode_row else "off"

    return {
        "total_usage_ms": total_usage,
        "top_apps": [
            {
                "package_name": r["package_name"],
                "app_name": r["app_name"],
                "total_ms": r["total_ms"],
            }
            for r in top_apps_rows
        ],
        "breach_count": breach_stats["count"] if breach_stats else 0,
        "total_breach_ms": breach_stats["total_ms"] if breach_stats else 0,
        "blocked_app_count": blocked_count,
        "native_block_mode": native_mode,
    }
