"""スタディルーム API ルート"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_pool
from api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.get("/{guild_id}")
async def get_campus(
    guild_id: int,
    current_user: dict = Depends(get_current_user),
):
    """キャンパス（全ルーム一覧）"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT r.*,
                   (SELECT COUNT(*) FROM room_members WHERE room_id = r.id)
                       AS member_count
            FROM study_rooms r
            WHERE r.guild_id = $1 AND r.state = 'active'
            ORDER BY r.created_at DESC
            """,
            guild_id,
        )

    return [
        {
            "id": r["id"],
            "guild_id": r["guild_id"],
            "name": r["name"],
            "description": r["description"],
            "theme": r["theme"],
            "collective_goal_minutes": r["collective_goal_minutes"],
            "collective_progress_minutes": r["collective_progress_minutes"],
            "max_occupants": r["max_occupants"],
            "member_count": r["member_count"],
            "state": r["state"],
        }
        for r in rows
    ]


@router.get("/{guild_id}/{room_id}")
async def get_room_detail(
    guild_id: int,
    room_id: int,
    current_user: dict = Depends(get_current_user),
):
    """ルーム詳細（メンバーリスト含む）"""
    pool = get_pool()
    async with pool.acquire() as conn:
        room = await conn.fetchrow(
            """
            SELECT r.*,
                   (SELECT COUNT(*) FROM room_members WHERE room_id = r.id)
                       AS member_count
            FROM study_rooms r
            WHERE r.id = $1 AND r.guild_id = $2
            """,
            room_id,
            guild_id,
        )
        if not room:
            raise HTTPException(status_code=404, detail="ルームが見つかりません")

        members = await conn.fetch(
            """
            SELECT rm.user_id, u.username, rm.platform,
                   rm.topic, rm.joined_at
            FROM room_members rm
            JOIN users u ON u.user_id = rm.user_id
            WHERE rm.room_id = $1
            ORDER BY rm.joined_at
            """,
            room_id,
        )

    return {
        "id": room["id"],
        "guild_id": room["guild_id"],
        "name": room["name"],
        "description": room["description"],
        "theme": room["theme"],
        "collective_goal_minutes": room["collective_goal_minutes"],
        "collective_progress_minutes": room["collective_progress_minutes"],
        "max_occupants": room["max_occupants"],
        "member_count": room["member_count"],
        "members": [
            {
                "user_id": m["user_id"],
                "username": m["username"],
                "platform": m["platform"],
                "topic": m["topic"],
                "joined_at": m["joined_at"].isoformat(),
            }
            for m in members
        ],
    }


@router.post("/{guild_id}/{room_id}/join")
async def join_room(
    guild_id: int,
    room_id: int,
    body: dict = {},
    current_user: dict = Depends(get_current_user),
):
    """Web参加"""
    pool = get_pool()
    user_id = current_user["user_id"]
    topic = body.get("topic", "")

    async with pool.acquire() as conn:
        room = await conn.fetchrow(
            "SELECT * FROM study_rooms WHERE id = $1 AND guild_id = $2",
            room_id,
            guild_id,
        )
        if not room:
            raise HTTPException(status_code=404, detail="ルームが見つかりません")

        member_count = await conn.fetchval(
            "SELECT COUNT(*) FROM room_members WHERE room_id = $1", room_id
        )
        if member_count >= room["max_occupants"]:
            raise HTTPException(status_code=409, detail="ルームが満員です")

        # Leave any existing room
        await conn.execute("DELETE FROM room_members WHERE user_id = $1", user_id)

        await conn.execute(
            """
            INSERT INTO room_members (room_id, user_id, platform, topic)
            VALUES ($1, $2, 'web', $3)
            ON CONFLICT (room_id, user_id) DO UPDATE
                SET platform = 'web', topic = $3, joined_at = NOW()
            """,
            room_id,
            user_id,
            topic,
        )

    # Publish event
    try:
        from api.services.redis_client import get_redis

        redis_conn = get_redis()
        if redis_conn:
            await redis_conn.publish(
                "studybot:events",
                json.dumps(
                    {
                        "type": "room_join",
                        "data": {
                            "room_id": room_id,
                            "user_id": user_id,
                            "platform": "web",
                            "topic": topic,
                            "guild_id": guild_id,
                        },
                    }
                ),
            )
    except Exception:
        logger.debug("room_joinイベント発行失敗", exc_info=True)

    return {"status": "joined", "room_id": room_id}


@router.post("/{guild_id}/{room_id}/leave")
async def leave_room(
    guild_id: int,
    room_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Web退出"""
    pool = get_pool()
    user_id = current_user["user_id"]

    async with pool.acquire() as conn:
        member = await conn.fetchrow(
            "SELECT * FROM room_members WHERE room_id = $1 AND user_id = $2",
            room_id,
            user_id,
        )
        if not member:
            raise HTTPException(status_code=404, detail="ルームに参加していません")

        await conn.execute(
            "DELETE FROM room_members WHERE room_id = $1 AND user_id = $2",
            room_id,
            user_id,
        )

        # Record history
        joined_at = member["joined_at"]
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        if joined_at.tzinfo is None:
            joined_at = joined_at.replace(tzinfo=timezone.utc)
        duration = int((now - joined_at).total_seconds() / 60)

        await conn.execute(
            """
            INSERT INTO room_history
                (room_id, user_id, platform, joined_at, duration_minutes)
            VALUES ($1, $2, $3, $4, $5)
            """,
            room_id,
            user_id,
            member["platform"],
            joined_at,
            duration,
        )

        # Update collective progress
        if duration > 0:
            await conn.execute(
                """
                UPDATE study_rooms
                SET collective_progress_minutes =
                    collective_progress_minutes + $2
                WHERE id = $1
                """,
                room_id,
                duration,
            )

    # Publish event
    try:
        from api.services.redis_client import get_redis

        redis_conn = get_redis()
        if redis_conn:
            await redis_conn.publish(
                "studybot:events",
                json.dumps(
                    {
                        "type": "room_leave",
                        "data": {
                            "room_id": room_id,
                            "user_id": user_id,
                            "guild_id": guild_id,
                            "duration_minutes": duration,
                        },
                    }
                ),
            )
    except Exception:
        logger.debug("room_leaveイベント発行失敗", exc_info=True)

    return {"status": "left", "duration_minutes": duration}


@router.get("/{guild_id}/{room_id}/history")
async def get_room_history(
    guild_id: int,
    room_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """ルーム利用履歴"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT rh.user_id, u.username, rh.platform,
                   rh.joined_at, rh.left_at, rh.duration_minutes
            FROM room_history rh
            JOIN users u ON u.user_id = rh.user_id
            WHERE rh.room_id = $1
            ORDER BY rh.left_at DESC
            LIMIT $2
            """,
            room_id,
            limit,
        )

    return [
        {
            "user_id": r["user_id"],
            "username": r["username"],
            "platform": r["platform"],
            "joined_at": r["joined_at"].isoformat(),
            "left_at": r["left_at"].isoformat() if r["left_at"] else None,
            "duration_minutes": r["duration_minutes"],
        }
        for r in rows
    ]
