"""サーバー統計ルート"""

from fastapi import APIRouter, Depends

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import ServerMember, ServerStats

router = APIRouter(prefix="/api/server", tags=["server"])


@router.get("/{guild_id}/stats", response_model=ServerStats)
async def get_server_stats(
    guild_id: int,
    current_user: dict = Depends(get_current_user),
):
    """サーバー全体の統計を取得"""
    pool = get_pool()
    async with pool.acquire() as conn:
        member_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT user_id) FROM study_logs WHERE guild_id = $1",
            guild_id,
        )

        total = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes,
                   COUNT(*) as session_count
            FROM study_logs WHERE guild_id = $1
            """,
            guild_id,
        )

        weekly = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes,
                   COUNT(DISTINCT user_id) as active_members
            FROM study_logs
            WHERE guild_id = $1
              AND logged_at >= CURRENT_DATE - INTERVAL '7 days'
            """,
            guild_id,
        )

        tasks = await conn.fetchval(
            "SELECT COUNT(*) FROM todos WHERE guild_id = $1 AND status = 'completed'",
            guild_id,
        )

        raids = await conn.fetchval(
            "SELECT COUNT(*) FROM study_raids WHERE guild_id = $1 AND state = 'completed'",
            guild_id,
        )

    return ServerStats(
        member_count=member_count or 0,
        total_minutes=total["total_minutes"] if total else 0,
        total_sessions=total["session_count"] if total else 0,
        weekly_minutes=weekly["total_minutes"] if weekly else 0,
        weekly_active_members=weekly["active_members"] if weekly else 0,
        tasks_completed=tasks or 0,
        raids_completed=raids or 0,
    )


@router.get("/{guild_id}/members", response_model=list[ServerMember])
async def get_server_members(
    guild_id: int,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """メンバー一覧 + 基本統計"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT u.user_id, u.username,
                   COALESCE(ul.xp, 0) as xp,
                   COALESCE(ul.level, 1) as level,
                   COALESCE(sl.total_minutes, 0) as total_study_minutes
            FROM users u
            LEFT JOIN user_levels ul ON ul.user_id = u.user_id
            LEFT JOIN (
                SELECT user_id, SUM(duration_minutes) as total_minutes
                FROM study_logs WHERE guild_id = $1
                GROUP BY user_id
            ) sl ON sl.user_id = u.user_id
            WHERE sl.total_minutes IS NOT NULL
            ORDER BY COALESCE(ul.xp, 0) DESC
            LIMIT $2
            """,
            guild_id,
            limit,
        )

    return [
        ServerMember(
            user_id=row["user_id"],
            username=row["username"],
            xp=row["xp"],
            level=row["level"],
            total_study_minutes=row["total_study_minutes"],
        )
        for row in rows
    ]


@router.get("/{guild_id}/vc-stats")
async def get_vc_stats(
    guild_id: int,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
):
    """VC勉強統計"""
    pool = get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes,
                   COUNT(*) as session_count,
                   COUNT(DISTINCT user_id) as unique_users
            FROM vc_sessions
            WHERE guild_id = $1
              AND started_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
            """,
            guild_id,
            days,
        )

        ranking = await conn.fetch(
            """
            SELECT vs.user_id, u.username,
                   SUM(vs.duration_minutes) as total_minutes
            FROM vc_sessions vs
            JOIN users u ON u.user_id = vs.user_id
            WHERE vs.guild_id = $1
              AND vs.started_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
            GROUP BY vs.user_id, u.username
            ORDER BY total_minutes DESC
            LIMIT 10
            """,
            guild_id,
            days,
        )

    return {
        "total_minutes": total["total_minutes"] if total else 0,
        "session_count": total["session_count"] if total else 0,
        "unique_users": total["unique_users"] if total else 0,
        "ranking": [dict(r) for r in ranking],
    }
