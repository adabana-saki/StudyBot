"""チャレンジルート"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import (
    ChallengeCheckinRequest,
    ChallengeDetailResponse,
    ChallengeLeaderboardEntry,
    ChallengeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


@router.get("", response_model=list[ChallengeResponse])
async def list_challenges(
    guild_id: int = Query(default=0),
    status: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """チャレンジ一覧"""
    pool = get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT c.*, u.username AS creator_name,
                   (SELECT COUNT(*)
                    FROM challenge_participants
                    WHERE challenge_id = c.id) AS participant_count
            FROM challenges c
            JOIN users u ON u.user_id = c.creator_id
            WHERE c.guild_id = $1
        """
        params: list = [guild_id]
        if status:
            params.append(status)
            query += f" AND c.status = ${len(params)}"
        query += " ORDER BY c.created_at DESC"
        rows = await conn.fetch(query, *params)

    return [
        ChallengeResponse(
            id=r["id"],
            creator_id=r["creator_id"],
            creator_name=r["creator_name"],
            guild_id=r["guild_id"],
            name=r["name"],
            description=r["description"] or "",
            goal_type=r["goal_type"],
            goal_target=r["goal_target"],
            duration_days=r["duration_days"],
            start_date=r["start_date"],
            end_date=r["end_date"],
            xp_multiplier=r["xp_multiplier"],
            status=r["status"],
            participant_count=r["participant_count"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/{challenge_id}", response_model=ChallengeDetailResponse)
async def get_challenge_detail(
    challenge_id: int,
    current_user: dict = Depends(get_current_user),
):
    """チャレンジ詳細"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT c.*, u.username AS creator_name,
                   (SELECT COUNT(*)
                    FROM challenge_participants
                    WHERE challenge_id = c.id) AS participant_count
            FROM challenges c
            JOIN users u ON u.user_id = c.creator_id
            WHERE c.id = $1
            """,
            challenge_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="チャレンジが見つかりません")

        participants = await conn.fetch(
            """
            SELECT cp.*, u.username FROM challenge_participants cp
            JOIN users u ON u.user_id = cp.user_id
            WHERE cp.challenge_id = $1
            ORDER BY cp.progress DESC
            """,
            challenge_id,
        )

    return ChallengeDetailResponse(
        id=row["id"],
        creator_id=row["creator_id"],
        creator_name=row["creator_name"],
        guild_id=row["guild_id"],
        name=row["name"],
        description=row["description"] or "",
        goal_type=row["goal_type"],
        goal_target=row["goal_target"],
        duration_days=row["duration_days"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        xp_multiplier=row["xp_multiplier"],
        status=row["status"],
        participant_count=row["participant_count"],
        created_at=row["created_at"],
        participants=[
            ChallengeLeaderboardEntry(
                user_id=p["user_id"],
                username=p["username"],
                progress=p["progress"],
                checkins=p["checkins"],
                completed=p["completed"],
            )
            for p in participants
        ],
    )


@router.post("/{challenge_id}/join")
async def join_challenge(
    challenge_id: int,
    current_user: dict = Depends(get_current_user),
):
    """チャレンジに参加"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        challenge = await conn.fetchrow(
            "SELECT * FROM challenges WHERE id = $1 AND status = 'active'",
            challenge_id,
        )
        if not challenge:
            raise HTTPException(
                status_code=404,
                detail="アクティブなチャレンジが見つかりません",
            )

        existing = await conn.fetchrow(
            "SELECT id FROM challenge_participants WHERE challenge_id = $1 AND user_id = $2",
            challenge_id,
            user_id,
        )
        if existing:
            raise HTTPException(status_code=400, detail="既に参加しています")

        await conn.execute(
            "INSERT INTO challenge_participants (challenge_id, user_id) VALUES ($1, $2)",
            challenge_id,
            user_id,
        )
    return {"message": "チャレンジに参加しました"}


@router.post("/{challenge_id}/checkin")
async def checkin(
    challenge_id: int,
    data: ChallengeCheckinRequest,
    current_user: dict = Depends(get_current_user),
):
    """チェックイン"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        participant = await conn.fetchrow(
            "SELECT * FROM challenge_participants WHERE challenge_id = $1 AND user_id = $2",
            challenge_id,
            user_id,
        )
        if not participant:
            raise HTTPException(
                status_code=404,
                detail="このチャレンジに参加していません",
            )

        today = date.today()
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO challenge_checkins
                    (challenge_id, user_id, checkin_date, progress_delta, note)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (challenge_id, user_id, checkin_date) DO UPDATE SET
                    progress_delta = challenge_checkins.progress_delta + $4
                """,
                challenge_id,
                user_id,
                today,
                data.progress,
                data.note or "",
            )
            await conn.execute(
                """
                UPDATE challenge_participants
                SET progress = progress + $3,
                    checkins = checkins + 1,
                    last_checkin_date = $4,
                    completed = (
                        progress + $3 >= (
                            SELECT goal_target
                            FROM challenges
                            WHERE id = $1
                        )
                    )
                WHERE challenge_id = $1 AND user_id = $2
                """,
                challenge_id,
                user_id,
                data.progress,
                today,
            )

    return {"message": "チェックイン完了"}


@router.get(
    "/{challenge_id}/leaderboard",
    response_model=list[ChallengeLeaderboardEntry],
)
async def get_leaderboard(
    challenge_id: int,
    current_user: dict = Depends(get_current_user),
):
    """リーダーボード"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT cp.*, u.username FROM challenge_participants cp
            JOIN users u ON u.user_id = cp.user_id
            WHERE cp.challenge_id = $1
            ORDER BY cp.progress DESC, cp.checkins DESC
            """,
            challenge_id,
        )
    return [
        ChallengeLeaderboardEntry(
            user_id=r["user_id"],
            username=r["username"],
            progress=r["progress"],
            checkins=r["checkins"],
            completed=r["completed"],
        )
        for r in rows
    ]
