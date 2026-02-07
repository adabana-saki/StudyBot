"""フォーカスセッション DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FocusRepository(BaseRepository):
    """フォーカスセッションのCRUD"""

    async def create_session(
        self,
        user_id: int,
        guild_id: int,
        duration_minutes: int,
        whitelisted_channels: list[int] | None = None,
    ) -> dict:
        """新しいフォーカスセッションを作成"""
        channels = whitelisted_channels or []
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO focus_sessions
                    (user_id, guild_id, duration_minutes, whitelisted_channels, state, started_at)
                VALUES ($1, $2, $3, $4, 'active', $5)
                RETURNING *
                """,
                user_id,
                guild_id,
                duration_minutes,
                channels,
                datetime.now(UTC),
            )
        return dict(row)

    async def get_active_session(self, user_id: int) -> dict | None:
        """アクティブなフォーカスセッションを取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM focus_sessions
                WHERE user_id = $1 AND state = 'active'
                ORDER BY started_at DESC LIMIT 1
                """,
                user_id,
            )
        return dict(row) if row else None

    async def end_session(self, session_id: int) -> dict | None:
        """フォーカスセッションを終了"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE focus_sessions
                SET state = 'completed', ended_at = $2
                WHERE id = $1
                RETURNING *
                """,
                session_id,
                datetime.now(UTC),
            )
        return dict(row) if row else None

    async def add_whitelist_channel(self, session_id: int, channel_id: int) -> None:
        """ホワイトリストにチャンネルを追加"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE focus_sessions
                SET whitelisted_channels = array_append(whitelisted_channels, $2)
                WHERE id = $1
                """,
                session_id,
                channel_id,
            )

    async def get_completed_sessions(self, user_id: int, days: int = 7) -> list[dict]:
        """完了したフォーカスセッション一覧を取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM focus_sessions
                WHERE user_id = $1
                  AND state = 'completed'
                  AND ended_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
                ORDER BY ended_at DESC
                """,
                user_id,
                days,
            )
        return [dict(row) for row in rows]
