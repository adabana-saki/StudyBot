"""統計ルート"""

from fastapi import APIRouter, Depends

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import DailyStudy, StudyStats, UserProfile

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/me", response_model=UserProfile)
async def get_my_stats(current_user: dict = Depends(get_current_user)):
    """自分の統計を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
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
        username=current_user["username"],
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
