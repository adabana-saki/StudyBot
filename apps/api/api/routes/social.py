"""ソーシャルタイムライン API ルート"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("/{guild_id}")
async def get_timeline(
    guild_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """タイムライン取得（リアクション数・コメント数付き）"""
    pool = get_pool()
    my_user_id = current_user["user_id"]

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM activity_events WHERE guild_id = $1",
            guild_id,
        )

        rows = await conn.fetch(
            """
            SELECT ae.id, ae.user_id, u.username, ae.event_type,
                   ae.event_data, ae.created_at,
                   COALESCE(rc.reaction_counts, '{}') AS reaction_counts,
                   COALESCE(cc.comment_count, 0) AS comment_count
            FROM activity_events ae
            JOIN users u ON u.user_id = ae.user_id
            LEFT JOIN LATERAL (
                SELECT jsonb_object_agg(reaction_type, cnt) AS reaction_counts
                FROM (
                    SELECT reaction_type, COUNT(*) AS cnt
                    FROM activity_reactions
                    WHERE event_id = ae.id
                    GROUP BY reaction_type
                ) sub
            ) rc ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS comment_count
                FROM activity_comments
                WHERE event_id = ae.id
            ) cc ON TRUE
            WHERE ae.guild_id = $1
            ORDER BY ae.created_at DESC
            OFFSET $2 LIMIT $3
            """,
            guild_id,
            offset,
            limit,
        )

        # Get current user's reactions for these events
        event_ids = [r["id"] for r in rows]
        my_reactions_rows = []
        if event_ids:
            my_reactions_rows = await conn.fetch(
                """
                SELECT event_id, reaction_type
                FROM activity_reactions
                WHERE event_id = ANY($1) AND user_id = $2
                """,
                event_ids,
                my_user_id,
            )

    my_reactions_map: dict[int, list[str]] = {}
    for r in my_reactions_rows:
        my_reactions_map.setdefault(r["event_id"], []).append(r["reaction_type"])

    items = []
    for r in rows:
        event_data = r["event_data"]
        if isinstance(event_data, str):
            event_data = json.loads(event_data)
        reaction_counts = r["reaction_counts"]
        if isinstance(reaction_counts, str):
            reaction_counts = json.loads(reaction_counts)

        items.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "username": r["username"],
            "event_type": r["event_type"],
            "event_data": event_data,
            "created_at": r["created_at"].isoformat(),
            "reaction_counts": reaction_counts or {},
            "my_reactions": my_reactions_map.get(r["id"], []),
            "comment_count": r["comment_count"],
        })

    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.post("/{event_id}/reactions")
async def add_reaction(
    event_id: int,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """リアクション追加"""
    reaction_type = body.get("reaction_type", "applaud")
    valid_types = {"applaud", "fire", "heart", "study_on"}
    if reaction_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"無効なリアクションタイプ: {reaction_type}",
        )

    pool = get_pool()
    user_id = current_user["user_id"]

    async with pool.acquire() as conn:
        # Verify event exists
        event = await conn.fetchrow(
            "SELECT id, user_id FROM activity_events WHERE id = $1", event_id
        )
        if not event:
            raise HTTPException(status_code=404, detail="イベントが見つかりません")

        await conn.execute(
            """
            INSERT INTO activity_reactions (event_id, user_id, reaction_type)
            VALUES ($1, $2, $3)
            ON CONFLICT (event_id, user_id, reaction_type) DO NOTHING
            """,
            event_id,
            user_id,
            reaction_type,
        )

    # Publish event for DM notification
    try:
        from api.services.redis_client import get_redis
        redis_conn = get_redis()
        if redis_conn:
            import json as json_mod
            await redis_conn.publish(
                "studybot:events",
                json_mod.dumps({
                    "type": "social_reaction",
                    "data": {
                        "event_id": event_id,
                        "target_user_id": event["user_id"],
                        "actor_user_id": user_id,
                        "actor_username": current_user["username"],
                        "reaction_type": reaction_type,
                    },
                }),
            )
    except Exception:
        logger.debug("リアクションイベント発行失敗", exc_info=True)

    return {"status": "ok"}


@router.delete("/{event_id}/reactions/{reaction_type}")
async def remove_reaction(
    event_id: int,
    reaction_type: str,
    current_user: dict = Depends(get_current_user),
):
    """リアクション削除"""
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM activity_reactions
            WHERE event_id = $1 AND user_id = $2 AND reaction_type = $3
            """,
            event_id,
            current_user["user_id"],
            reaction_type,
        )
    return {"status": "ok"}


@router.get("/{event_id}/comments")
async def get_comments(
    event_id: int,
    current_user: dict = Depends(get_current_user),
):
    """コメント一覧"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ac.id, ac.user_id, u.username, ac.body, ac.created_at
            FROM activity_comments ac
            JOIN users u ON u.user_id = ac.user_id
            WHERE ac.event_id = $1
            ORDER BY ac.created_at ASC
            """,
            event_id,
        )

    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "username": r["username"],
            "body": r["body"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.post("/{event_id}/comments")
async def add_comment(
    event_id: int,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """コメント投稿"""
    comment_body = body.get("body", "").strip()
    if not comment_body or len(comment_body) > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="コメントは1-500文字で入力してください",
        )

    pool = get_pool()
    user_id = current_user["user_id"]

    async with pool.acquire() as conn:
        event = await conn.fetchrow(
            "SELECT id, user_id FROM activity_events WHERE id = $1", event_id
        )
        if not event:
            raise HTTPException(status_code=404, detail="イベントが見つかりません")

        row = await conn.fetchrow(
            """
            INSERT INTO activity_comments (event_id, user_id, body)
            VALUES ($1, $2, $3)
            RETURNING id, created_at
            """,
            event_id,
            user_id,
            comment_body,
        )

    # Publish event for DM notification
    try:
        from api.services.redis_client import get_redis
        redis_conn = get_redis()
        if redis_conn:
            import json as json_mod
            await redis_conn.publish(
                "studybot:events",
                json_mod.dumps({
                    "type": "social_comment",
                    "data": {
                        "event_id": event_id,
                        "target_user_id": event["user_id"],
                        "actor_user_id": user_id,
                        "actor_username": current_user["username"],
                        "body": comment_body,
                    },
                }),
            )
    except Exception:
        logger.debug("コメントイベント発行失敗", exc_info=True)

    return {
        "id": row["id"],
        "user_id": user_id,
        "username": current_user["username"],
        "body": comment_body,
        "created_at": row["created_at"].isoformat(),
    }


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: dict = Depends(get_current_user),
):
    """コメント削除（own only）"""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM activity_comments WHERE id = $1",
            comment_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="コメントが見つかりません")
        if row["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="自分のコメントのみ削除できます")

        await conn.execute("DELETE FROM activity_comments WHERE id = $1", comment_id)

    return {"status": "ok"}
