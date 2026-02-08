"""セッションルート"""

import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import ActiveSessionResponse, SessionStartRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/active", response_model=list[ActiveSessionResponse])
async def get_active_sessions(current_user: dict = Depends(get_current_user)):
    """全アクティブセッションを取得"""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT acs.*, u.username
            FROM active_cross_sessions acs
            JOIN users u ON u.user_id = acs.user_id
            WHERE acs.state = 'active' AND acs.end_time > NOW()
            ORDER BY acs.started_at DESC
            LIMIT 50
            """
        )

    now = datetime.now(UTC)
    return [
        ActiveSessionResponse(
            id=r["id"],
            user_id=r["user_id"],
            username=r["username"],
            session_type=r["session_type"],
            source_platform=r["source_platform"],
            topic=r["topic"] or "",
            duration_minutes=r["duration_minutes"],
            started_at=r["started_at"],
            end_time=r["end_time"],
            remaining_seconds=max(0, int((r["end_time"] - now).total_seconds())),
        )
        for r in rows
    ]


@router.post("/start", response_model=ActiveSessionResponse)
async def start_session(
    data: SessionStartRequest,
    current_user: dict = Depends(get_current_user),
):
    """Webからセッション開始"""
    user_id = current_user["user_id"]
    pool = get_pool()
    end_time = datetime.now(UTC) + timedelta(minutes=data.duration_minutes)

    async with pool.acquire() as conn:
        # 既存セッションを終了
        await conn.execute(
            """
            UPDATE active_cross_sessions SET state = 'completed'
            WHERE user_id = $1 AND state = 'active'
            """,
            user_id,
        )

        session_id = await conn.fetchval(
            """
            INSERT INTO active_cross_sessions
                (user_id, session_type, source_platform, topic, duration_minutes, end_time)
            VALUES ($1, $2, 'web', $3, $4, $5)
            RETURNING id
            """,
            user_id,
            data.session_type,
            data.topic or "",
            data.duration_minutes,
            end_time,
        )

    # Redis publish for bot notification
    try:
        from api.services.redis_client import get_redis

        redis = get_redis()
        await redis.publish(
            "studybot:sessions",
            json.dumps(
                {
                    "type": "session_sync",
                    "data": {
                        "user_id": user_id,
                        "session_type": data.session_type,
                        "source": "web",
                        "action": "start",
                        "topic": data.topic or "",
                    },
                }
            ),
        )
    except Exception:
        logger.warning("Redis publish失敗", exc_info=True)

    return ActiveSessionResponse(
        id=session_id,
        user_id=user_id,
        username=current_user.get("username", ""),
        session_type=data.session_type,
        source_platform="web",
        topic=data.topic or "",
        duration_minutes=data.duration_minutes,
        started_at=datetime.now(UTC),
        end_time=end_time,
        remaining_seconds=data.duration_minutes * 60,
    )


@router.post("/end")
async def end_session(current_user: dict = Depends(get_current_user)):
    """セッション終了"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE active_cross_sessions SET state = 'completed'
            WHERE user_id = $1 AND state = 'active'
            """,
            user_id,
        )

    # Redis publish
    try:
        from api.services.redis_client import get_redis

        redis = get_redis()
        await redis.publish(
            "studybot:sessions",
            json.dumps(
                {
                    "type": "session_sync",
                    "data": {
                        "user_id": user_id,
                        "session_type": "",
                        "source": "web",
                        "action": "end",
                    },
                }
            ),
        )
    except Exception:
        logger.warning("Redis publish失敗", exc_info=True)

    return {"message": "セッション終了"}
