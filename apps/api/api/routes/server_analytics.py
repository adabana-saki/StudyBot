"""サーバーコマンドセンター API ルート"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_pool
from api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/server", tags=["server-analytics"])


@router.get("/{guild_id}/analytics/engagement")
async def get_engagement(
    guild_id: int,
    days: int = Query(default=30, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """エンゲージメント推移"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                d.day::date AS date,
                COUNT(DISTINCT sl.user_id) AS active_users,
                COUNT(DISTINCT sl.id) AS sessions,
                COALESCE(SUM(sl.duration_minutes), 0) AS total_minutes
            FROM generate_series(
                CURRENT_DATE - ($2 || ' days')::interval,
                CURRENT_DATE,
                '1 day'
            ) d(day)
            LEFT JOIN study_logs sl
                ON sl.guild_id = $1
                AND sl.logged_at::date = d.day::date
            GROUP BY d.day
            ORDER BY d.day
            """,
            guild_id,
            str(days),
        )

    return [
        {
            "date": str(r["date"]),
            "active_users": r["active_users"],
            "sessions": r["sessions"],
            "total_minutes": r["total_minutes"],
        }
        for r in rows
    ]


@router.get("/{guild_id}/analytics/at-risk")
async def get_at_risk_members(
    guild_id: int,
    current_user: dict = Depends(get_current_user),
):
    """離脱リスクメンバー"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                ul.user_id,
                u.username,
                COALESCE(ul.best_streak, 0) AS best_streak,
                ul.last_study_date,
                CURRENT_DATE - ul.last_study_date AS days_inactive,
                CASE
                    WHEN CURRENT_DATE - ul.last_study_date >= 14 THEN 1.0
                    WHEN CURRENT_DATE - ul.last_study_date >= 7 THEN 0.7
                    ELSE 0.4
                END * LEAST(COALESCE(ul.best_streak, 0) / 10.0, 1.0) AS risk_score
            FROM user_levels ul
            JOIN users u ON u.user_id = ul.user_id
            JOIN study_logs sl ON sl.user_id = ul.user_id AND sl.guild_id = $1
            WHERE ul.last_study_date IS NOT NULL
              AND ul.last_study_date < CURRENT_DATE - INTERVAL '3 days'
              AND ul.last_study_date > CURRENT_DATE - INTERVAL '60 days'
              AND COALESCE(ul.best_streak, 0) >= 3
            GROUP BY ul.user_id, u.username, ul.best_streak, ul.last_study_date
            ORDER BY risk_score DESC
            LIMIT 50
            """,
            guild_id,
        )

    return [
        {
            "user_id": r["user_id"],
            "username": r["username"],
            "best_streak": r["best_streak"],
            "last_study_date": str(r["last_study_date"]) if r["last_study_date"] else None,
            "days_inactive": r["days_inactive"],
            "risk_score": round(float(r["risk_score"]), 2),
        }
        for r in rows
    ]


@router.get("/{guild_id}/analytics/topics")
async def get_topic_analysis(
    guild_id: int,
    current_user: dict = Depends(get_current_user),
):
    """トピック分析"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                COALESCE(NULLIF(topic, ''), 'その他') AS topic,
                COUNT(*) AS count,
                SUM(duration_minutes) AS total_minutes,
                COUNT(*) FILTER (
                    WHERE logged_at >= NOW() - INTERVAL '7 days'
                ) AS this_week,
                COUNT(*) FILTER (
                    WHERE logged_at >= NOW() - INTERVAL '14 days'
                      AND logged_at < NOW() - INTERVAL '7 days'
                ) AS last_week
            FROM study_logs
            WHERE guild_id = $1
              AND logged_at >= NOW() - INTERVAL '30 days'
            GROUP BY COALESCE(NULLIF(topic, ''), 'その他')
            ORDER BY count DESC
            LIMIT 30
            """,
            guild_id,
        )

    return [
        {
            "topic": r["topic"],
            "count": r["count"],
            "total_minutes": r["total_minutes"],
            "this_week": r["this_week"],
            "last_week": r["last_week"],
        }
        for r in rows
    ]


@router.get("/{guild_id}/analytics/optimal-times")
async def get_optimal_times(
    guild_id: int,
    current_user: dict = Depends(get_current_user),
):
    """最適イベント時間（ヒートマップデータ）"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                EXTRACT(DOW FROM logged_at)::int AS day_of_week,
                EXTRACT(HOUR FROM logged_at)::int AS hour,
                COUNT(*) AS session_count,
                SUM(duration_minutes) AS total_minutes
            FROM study_logs
            WHERE guild_id = $1
              AND logged_at >= NOW() - INTERVAL '30 days'
            GROUP BY day_of_week, hour
            ORDER BY day_of_week, hour
            """,
            guild_id,
        )

    return [
        {
            "day_of_week": r["day_of_week"],
            "hour": r["hour"],
            "session_count": r["session_count"],
            "total_minutes": r["total_minutes"],
        }
        for r in rows
    ]


@router.get("/{guild_id}/analytics/health")
async def get_community_health(
    guild_id: int,
    current_user: dict = Depends(get_current_user),
):
    """コミュニティ健全性スコア"""
    pool = get_pool()
    async with pool.acquire() as conn:
        # DAU/MAU ratio
        dau = (
            await conn.fetchval(
                """
            SELECT COUNT(DISTINCT user_id)
            FROM study_logs
            WHERE guild_id = $1
              AND logged_at >= CURRENT_DATE
            """,
                guild_id,
            )
            or 0
        )

        mau = (
            await conn.fetchval(
                """
            SELECT COUNT(DISTINCT user_id)
            FROM study_logs
            WHERE guild_id = $1
              AND logged_at >= NOW() - INTERVAL '30 days'
            """,
                guild_id,
            )
            or 1
        )

        dau_mau = round(dau / max(mau, 1), 3)

        # Average streak
        avg_streak = (
            await conn.fetchval(
                """
            SELECT COALESCE(AVG(streak_days), 0)
            FROM user_levels ul
            JOIN study_logs sl ON sl.user_id = ul.user_id AND sl.guild_id = $1
            GROUP BY sl.guild_id
            """,
                guild_id,
            )
            or 0.0
        )

        # Retention: users active this week who were active last week
        active_this_week = (
            await conn.fetchval(
                """
            SELECT COUNT(DISTINCT user_id)
            FROM study_logs
            WHERE guild_id = $1
              AND logged_at >= NOW() - INTERVAL '7 days'
            """,
                guild_id,
            )
            or 0
        )

        active_last_week = (
            await conn.fetchval(
                """
            SELECT COUNT(DISTINCT user_id)
            FROM study_logs
            WHERE guild_id = $1
              AND logged_at >= NOW() - INTERVAL '14 days'
              AND logged_at < NOW() - INTERVAL '7 days'
            """,
                guild_id,
            )
            or 1
        )

        retention = round(active_this_week / max(active_last_week, 1), 3)

        # Churn: users active last week but not this week
        churned = (
            await conn.fetchval(
                """
            SELECT COUNT(DISTINCT user_id)
            FROM study_logs
            WHERE guild_id = $1
              AND logged_at >= NOW() - INTERVAL '14 days'
              AND logged_at < NOW() - INTERVAL '7 days'
              AND user_id NOT IN (
                  SELECT DISTINCT user_id FROM study_logs
                  WHERE guild_id = $1
                    AND logged_at >= NOW() - INTERVAL '7 days'
              )
            """,
                guild_id,
            )
            or 0
        )

        churn_rate = round(churned / max(active_last_week, 1), 3)

    # Composite score: weighted average
    score = int(
        min(
            100,
            max(
                0,
                dau_mau * 100 * 0.25
                + retention * 100 * 0.3
                + min(float(avg_streak) / 7.0, 1.0) * 100 * 0.25
                + (1 - churn_rate) * 100 * 0.2,
            ),
        )
    )

    return {
        "score": score,
        "dau_mau_ratio": dau_mau,
        "retention_rate": retention,
        "avg_streak": round(float(avg_streak), 1),
        "churn_rate": churn_rate,
    }


@router.post("/{guild_id}/actions")
async def create_action(
    guild_id: int,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """アクション作成（即時実行 or スケジュール）"""
    action_type = body.get("action_type", "")
    action_data = body.get("action_data", {})
    scheduled_for = body.get("scheduled_for")

    valid_types = {"send_dm", "create_challenge", "create_raid", "announce"}
    if action_type not in valid_types:
        raise HTTPException(status_code=422, detail=f"無効なアクションタイプ: {action_type}")

    pool = get_pool()

    if scheduled_for:
        # Save to DB for later execution
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO scheduled_actions
                    (guild_id, action_type, action_data, scheduled_for, created_by)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, scheduled_for
                """,
                guild_id,
                action_type,
                json.dumps(action_data),
                scheduled_for,
                current_user["user_id"],
            )
        return {
            "id": row["id"],
            "status": "scheduled",
            "scheduled_for": row["scheduled_for"].isoformat(),
        }
    else:
        # Immediate execution via Redis
        try:
            from api.services.redis_client import get_redis

            redis_conn = get_redis()
            if redis_conn:
                await redis_conn.publish(
                    "studybot:admin_actions",
                    json.dumps(
                        {
                            "action_type": action_type,
                            "action_data": action_data,
                        }
                    ),
                )
                return {"status": "dispatched"}
            raise HTTPException(status_code=503, detail="Redis unavailable")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="アクション送信失敗")


@router.get("/{guild_id}/actions")
async def get_actions(
    guild_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """アクション履歴"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, action_type, action_data, scheduled_for,
                   executed, result, created_by, created_at
            FROM scheduled_actions
            WHERE guild_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            guild_id,
            limit,
        )

    return [
        {
            "id": r["id"],
            "action_type": r["action_type"],
            "action_data": json.loads(r["action_data"])
            if isinstance(r["action_data"], str)
            else r["action_data"],
            "scheduled_for": r["scheduled_for"].isoformat() if r["scheduled_for"] else None,
            "executed": r["executed"],
            "result": r["result"],
            "created_by": r["created_by"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
