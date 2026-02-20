"""統計ルート"""

from fastapi import APIRouter, Depends, Query

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import (
    DailyStudy,
    StudyLogCreateRequest,
    StudyLogEntry,
    StudyStats,
    UserProfile,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/me", response_model=UserProfile)
async def get_my_stats(current_user: dict = Depends(get_current_user)):
    """自分の統計を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        # ユーザー情報（アバター含む）
        user_row = await conn.fetchrow(
            "SELECT username, COALESCE(avatar_url, '') as avatar_url FROM users WHERE user_id = $1",
            user_id,
        )

        # レベル情報
        level_row = await conn.fetchrow(
            "SELECT xp, level, streak_days FROM user_levels WHERE user_id = $1",
            user_id,
        )

        # コイン残高
        coin_row = await conn.fetchrow(
            "SELECT balance FROM virtual_currency WHERE user_id = $1",
            user_id,
        )

        # ランク
        rank = await conn.fetchval(
            """
            SELECT COUNT(*) + 1 FROM user_levels
            WHERE xp > (SELECT COALESCE(xp, 0) FROM user_levels WHERE user_id = $1)
            """,
            user_id,
        )

    return UserProfile(
        user_id=user_id,
        username=user_row["username"] if user_row else current_user["username"],
        avatar_url=user_row["avatar_url"] if user_row else "",
        xp=level_row["xp"] if level_row else 0,
        level=level_row["level"] if level_row else 1,
        streak_days=level_row["streak_days"] if level_row else 0,
        coins=coin_row["balance"] if coin_row else 0,
        rank=rank or 0,
    )


@router.get("/me/study", response_model=StudyStats)
async def get_my_study_stats(
    period: str = "weekly",
    current_user: dict = Depends(get_current_user),
):
    """自分の学習統計を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    interval_map = {
        "daily": "1 day",
        "weekly": "7 days",
        "monthly": "30 days",
        "all_time": "36500 days",
    }
    interval = interval_map.get(period, "7 days")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            SELECT
                COALESCE(SUM(duration_minutes), 0) as total_minutes,
                COUNT(*) as session_count,
                COALESCE(AVG(duration_minutes), 0) as avg_minutes
            FROM study_logs
            WHERE user_id = $1
              AND logged_at >= CURRENT_TIMESTAMP - INTERVAL '{interval}'
            """,
            user_id,
        )

    return StudyStats(
        total_minutes=row["total_minutes"],
        session_count=row["session_count"],
        avg_minutes=float(row["avg_minutes"]),
        period=period,
    )


@router.get("/me/daily", response_model=list[DailyStudy])
async def get_daily_study(
    days: int = 14,
    current_user: dict = Depends(get_current_user),
):
    """日別学習時間を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DATE(logged_at) as day, SUM(duration_minutes) as total_minutes
            FROM study_logs
            WHERE user_id = $1
              AND logged_at >= CURRENT_DATE - $2
            GROUP BY DATE(logged_at)
            ORDER BY day
            """,
            user_id,
            days,
        )

    return [DailyStudy(day=row["day"], total_minutes=row["total_minutes"]) for row in rows]


@router.post("/me/log", response_model=StudyLogEntry)
async def create_study_log(
    request: StudyLogCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """手動で学習記録を作成"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO study_logs (user_id, guild_id, subject, duration_minutes, note)
            VALUES ($1, 0, $2, $3, $4)
            RETURNING id, subject, duration_minutes, note, logged_at
            """,
            user_id,
            request.subject or "",
            request.duration_minutes,
            request.note or "",
        )

    return StudyLogEntry(
        id=row["id"],
        subject=row["subject"],
        duration_minutes=row["duration_minutes"],
        note=row["note"],
        logged_at=row["logged_at"],
    )


@router.get("/me/logs", response_model=list[StudyLogEntry])
async def get_study_logs(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """学習記録一覧を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, subject, duration_minutes, note, logged_at
            FROM study_logs
            WHERE user_id = $1 AND logged_at >= CURRENT_DATE - $2
            ORDER BY logged_at DESC
            LIMIT 100
            """,
            user_id,
            days,
        )

    return [
        StudyLogEntry(
            id=r["id"],
            subject=r["subject"],
            duration_minutes=r["duration_minutes"],
            note=r["note"] or "",
            logged_at=r["logged_at"],
        )
        for r in rows
    ]
