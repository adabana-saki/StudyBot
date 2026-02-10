"""チームバトル API ルート"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_pool
from api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/battles", tags=["battles"])


@router.get("/{guild_id}")
async def get_battles(
    guild_id: int,
    current_user: dict = Depends(get_current_user),
):
    """アクティブバトル一覧"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT tb.*,
                   ta.name AS team_a_name,
                   tb2.name AS team_b_name,
                   (SELECT COUNT(*) FROM team_members WHERE team_id = tb.team_a_id)
                       AS team_a_members,
                   (SELECT COUNT(*) FROM team_members WHERE team_id = tb.team_b_id)
                       AS team_b_members
            FROM team_battles tb
            JOIN study_teams ta ON ta.id = tb.team_a_id
            JOIN study_teams tb2 ON tb2.id = tb.team_b_id
            WHERE tb.guild_id = $1
              AND tb.status IN ('pending', 'active')
            ORDER BY tb.created_at DESC
            """,
            guild_id,
        )

    return [
        {
            "id": r["id"],
            "guild_id": r["guild_id"],
            "goal_type": r["goal_type"],
            "duration_days": r["duration_days"],
            "start_date": str(r["start_date"]),
            "end_date": str(r["end_date"]),
            "status": r["status"],
            "xp_multiplier": r["xp_multiplier"],
            "team_a": {
                "team_id": r["team_a_id"],
                "name": r["team_a_name"],
                "score": r["team_a_score"],
                "member_count": r["team_a_members"],
            },
            "team_b": {
                "team_id": r["team_b_id"],
                "name": r["team_b_name"],
                "score": r["team_b_score"],
                "member_count": r["team_b_members"],
            },
            "winner_team_id": r["winner_team_id"],
        }
        for r in rows
    ]


@router.get("/{guild_id}/{battle_id}")
async def get_battle_detail(
    guild_id: int,
    battle_id: int,
    current_user: dict = Depends(get_current_user),
):
    """バトル詳細"""
    pool = get_pool()
    async with pool.acquire() as conn:
        battle = await conn.fetchrow(
            """
            SELECT tb.*,
                   ta.name AS team_a_name,
                   tb2.name AS team_b_name,
                   (SELECT COUNT(*) FROM team_members WHERE team_id = tb.team_a_id)
                       AS team_a_members,
                   (SELECT COUNT(*) FROM team_members WHERE team_id = tb.team_b_id)
                       AS team_b_members
            FROM team_battles tb
            JOIN study_teams ta ON ta.id = tb.team_a_id
            JOIN study_teams tb2 ON tb2.id = tb.team_b_id
            WHERE tb.id = $1 AND tb.guild_id = $2
            """,
            battle_id,
            guild_id,
        )

        if not battle:
            raise HTTPException(status_code=404, detail="バトルが見つかりません")

        contributions = await conn.fetch(
            """
            SELECT bc.user_id, u.username, bc.team_id,
                   SUM(bc.contribution) AS total_contribution,
                   bc.source
            FROM battle_contributions bc
            JOIN users u ON u.user_id = bc.user_id
            WHERE bc.battle_id = $1
            GROUP BY bc.user_id, u.username, bc.team_id, bc.source
            ORDER BY total_contribution DESC
            """,
            battle_id,
        )

    return {
        "id": battle["id"],
        "guild_id": battle["guild_id"],
        "goal_type": battle["goal_type"],
        "duration_days": battle["duration_days"],
        "start_date": str(battle["start_date"]),
        "end_date": str(battle["end_date"]),
        "status": battle["status"],
        "xp_multiplier": battle["xp_multiplier"],
        "team_a": {
            "team_id": battle["team_a_id"],
            "name": battle["team_a_name"],
            "score": battle["team_a_score"],
            "member_count": battle["team_a_members"],
        },
        "team_b": {
            "team_id": battle["team_b_id"],
            "name": battle["team_b_name"],
            "score": battle["team_b_score"],
            "member_count": battle["team_b_members"],
        },
        "winner_team_id": battle["winner_team_id"],
        "contributions": [
            {
                "user_id": c["user_id"],
                "username": c["username"],
                "team_id": c["team_id"],
                "contribution": c["total_contribution"],
                "source": c["source"],
            }
            for c in contributions
        ],
    }
