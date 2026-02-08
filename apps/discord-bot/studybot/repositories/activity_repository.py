"""アクティビティリポジトリ"""

import json
import logging

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ActivityRepository(BaseRepository):
    """activity_events テーブル操作"""

    async def save_event(
        self, user_id: int, guild_id: int, event_type: str, event_data: dict
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO activity_events (user_id, guild_id, event_type, event_data)
                VALUES ($1, $2, $3, $4)
                """,
                user_id,
                guild_id,
                event_type,
                json.dumps(event_data),
            )

    async def get_recent(self, guild_id: int, limit: int = 50) -> list[dict]:
        async with self.db_pool.acquire() as conn:
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
            return [dict(r) for r in rows]

    async def get_studying_now(self, guild_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (ae.user_id) ae.user_id, u.username,
                       ae.event_type, ae.event_data, ae.created_at
                FROM activity_events ae
                JOIN users u ON u.user_id = ae.user_id
                WHERE ae.guild_id = $1
                  AND ae.event_type IN ('study_start', 'focus_start', 'pomodoro_complete')
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
            return [dict(r) for r in rows]
