"""ポモドーロセッション DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PomodoroRepository(BaseRepository):
    """ポモドーロセッションのCRUD"""

    async def get_active_session(self, user_id: int) -> dict | None:
        """アクティブなセッションを取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM pomodoro_sessions
                WHERE user_id = $1 AND state IN ('working', 'break', 'paused')
                ORDER BY created_at DESC LIMIT 1
                """,
                user_id,
            )
        return dict(row) if row else None

    async def create_session(
        self,
        user_id: int,
        guild_id: int,
        channel_id: int,
        topic: str,
        work_minutes: int,
        break_minutes: int,
    ) -> int:
        """新しいセッションを作成"""
        async with self.db_pool.acquire() as conn:
            session_id = await conn.fetchval(
                """
                INSERT INTO pomodoro_sessions
                    (user_id, guild_id, channel_id, topic, work_minutes, break_minutes,
                     state, started_at)
                VALUES ($1, $2, $3, $4, $5, $6, 'working', $7)
                RETURNING id
                """,
                user_id,
                guild_id,
                channel_id,
                topic,
                work_minutes,
                break_minutes,
                datetime.now(UTC),
            )
        return session_id

    async def update_state(
        self,
        session_id: int,
        state: str,
        **kwargs,
    ) -> None:
        """セッション状態を更新"""
        set_parts = ["state = $2"]
        values: list = [session_id, state]
        idx = 3

        for key, value in kwargs.items():
            set_parts.append(f"{key} = ${idx}")
            values.append(value)
            idx += 1

        query = f"""
            UPDATE pomodoro_sessions
            SET {", ".join(set_parts)}
            WHERE id = $1
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, *values)

    async def get_completed_sessions(
        self, user_id: int, since: datetime | None = None
    ) -> list[dict]:
        """完了セッション一覧を取得"""
        query = """
            SELECT * FROM pomodoro_sessions
            WHERE user_id = $1 AND state = 'completed'
        """
        params: list = [user_id]

        if since:
            query += " AND ended_at >= $2"
            params.append(since)

        query += " ORDER BY ended_at DESC"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
