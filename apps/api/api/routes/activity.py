"""アクティビティルート"""

import json
import logging

from fastapi import APIRouter, Depends, Query

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import ActivityEventResponse, ActiveStudierResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("/{guild_id}", response_model=list[ActivityEventResponse])
async def get_activity_feed(
    guild_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """ギルドのアクティビティフィードを取得"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ae.id, ae.user_id, u.username, ae.event_type,
                   ae.event_data, ae.created_at
            FROM activity_events ae
            JOIN users u ON u.user_id = ae.user_id
            WHERE ae.guild_id = $1
            ORDER BY ae.created_at DESC
            LIMIT $2
            """,
            guild_id,
            limit,
        )

    return [
        ActivityEventResponse(
            id=r["id"],
            user_id=r["user_id"],
            username=r["username"],
            event_type=r["event_type"],
            event_data=json.loads(r["event_data"])
            if isinstance(r["event_data"], str)
            else r["event_data"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/{guild_id}/studying-now", response_model=list[ActiveStudierResponse])
async def get_studying_now(
    guild_id: int,
    current_user: dict = Depends(get_current_user),
):
    """現在勉強中のユーザーを取得"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (ae.user_id) ae.user_id, u.username,
                   ae.event_type, ae.event_data, ae.created_at
            FROM activity_events ae
            JOIN users u ON u.user_id = ae.user_id
            WHERE ae.guild_id = $1
              AND ae.event_type IN ('study_start', 'focus_start')
              AND ae.created_at > NOW() - INTERVAL '3 hours'
              AND NOT EXISTS (
                  SELECT 1 FROM activity_events ae2
                  WHERE ae2.user_id = ae.user_id
                    AND ae2.guild_id = ae.guild_id
                    AND ae2.event_type IN ('study_end', 'focus_end')
                    AND ae2.created_at > ae.created_at
              )
            ORDER BY ae.user_id, ae.created_at DESC
            """,
            guild_id,
        )

    return [
        ActiveStudierResponse(
            user_id=r["user_id"],
            username=r["username"],
            event_type=r["event_type"],
            event_data=json.loads(r["event_data"])
            if isinstance(r["event_data"], str)
            else r["event_data"],
            started_at=r["created_at"],
        )
        for r in rows
    ]
