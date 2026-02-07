"""リーダーボードルート"""

from fastapi import APIRouter, Query

from api.database import get_pool
from api.models.schemas import LeaderboardEntry, LeaderboardResponse

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("/{guild_id}", response_model=LeaderboardResponse)
async def get_leaderboard(
    guild_id: int,
    category: str = Query("xp", regex="^(xp|study|tasks)$"),
    period: str = Query("all_time", regex="^(weekly|monthly|all_time)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """ギルドリーダーボードを取得"""
    pool = get_pool()

    interval_map = {
        "weekly": "7 days",
        "monthly": "30 days",
        "all_time": "36500 days",
    }
    interval = interval_map.get(period, "36500 days")

    async with pool.acquire() as conn:
        if category == "xp":
            rows = await conn.fetch(
                """
                SELECT ul.user_id, u.username, ul.xp as value, ul.level
                FROM user_levels ul
                JOIN users u ON u.user_id = ul.user_id
                ORDER BY ul.xp DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        elif category == "study":
            rows = await conn.fetch(
                f"""
                SELECT sl.user_id, u.username,
                       COALESCE(SUM(sl.duration_minutes), 0)::int as value,
                       COALESCE(ul.level, 1) as level
                FROM study_logs sl
                JOIN users u ON u.user_id = sl.user_id
                LEFT JOIN user_levels ul ON ul.user_id = sl.user_id
                WHERE sl.guild_id = $1
                  AND sl.logged_at >= CURRENT_TIMESTAMP - INTERVAL '{interval}'
                GROUP BY sl.user_id, u.username, ul.level
                ORDER BY value DESC
                LIMIT $2 OFFSET $3
                """,
                guild_id,
                limit,
                offset,
            )
        else:  # tasks
            rows = await conn.fetch(
                f"""
                SELECT t.user_id, u.username,
                       COUNT(*)::int as value,
                       COALESCE(ul.level, 1) as level
                FROM todos t
                JOIN users u ON u.user_id = t.user_id
                LEFT JOIN user_levels ul ON ul.user_id = t.user_id
                WHERE t.guild_id = $1
                  AND t.status = 'completed'
                  AND t.completed_at >= CURRENT_TIMESTAMP - INTERVAL '{interval}'
                GROUP BY t.user_id, u.username, ul.level
                ORDER BY value DESC
                LIMIT $2 OFFSET $3
                """,
                guild_id,
                limit,
                offset,
            )

    entries = [
        LeaderboardEntry(
            rank=offset + i + 1,
            user_id=row["user_id"],
            username=row["username"],
            value=row["value"],
            level=row.get("level"),
        )
        for i, row in enumerate(rows)
    ]

    return LeaderboardResponse(category=category, period=period, entries=entries)
