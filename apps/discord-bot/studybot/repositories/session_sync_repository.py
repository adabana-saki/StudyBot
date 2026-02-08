"""セッション同期リポジトリ"""

import logging
from datetime import datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class SessionSyncRepository(BaseRepository):
    """active_cross_sessions テーブル操作"""

    async def create_session(
        self,
        user_id: int,
        session_type: str,
        source_platform: str,
        duration_minutes: int,
        end_time: datetime,
        topic: str = "",
        session_ref_id: int | None = None,
    ) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO active_cross_sessions
                    (user_id, session_type, source_platform, session_ref_id,
                     topic, duration_minutes, end_time)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                user_id,
                session_type,
                source_platform,
                session_ref_id,
                topic,
                duration_minutes,
                end_time,
            )

    async def get_active_session(self, user_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM active_cross_sessions
                WHERE user_id = $1 AND state = 'active'
                ORDER BY started_at DESC LIMIT 1
                """,
                user_id,
            )
            return dict(row) if row else None

    async def get_active_sessions(self, limit: int = 50) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT acs.*, u.username
                FROM active_cross_sessions acs
                JOIN users u ON u.user_id = acs.user_id
                WHERE acs.state = 'active'
                ORDER BY acs.started_at DESC
                LIMIT $1
                """,
                limit,
            )
            return [dict(r) for r in rows]

    async def end_session(self, session_id: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE active_cross_sessions
                SET state = 'completed', end_time = NOW()
                WHERE id = $1
                """,
                session_id,
            )

    async def end_user_sessions(self, user_id: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE active_cross_sessions
                SET state = 'completed'
                WHERE user_id = $1 AND state = 'active'
                """,
                user_id,
            )

    async def cleanup_expired(self) -> int:
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE active_cross_sessions
                SET state = 'expired'
                WHERE state = 'active' AND end_time < NOW()
                """
            )
            return int(result.split()[-1]) if result else 0
