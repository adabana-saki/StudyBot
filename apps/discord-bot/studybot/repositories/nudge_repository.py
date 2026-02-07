"""スマホ通知 DB操作"""

import logging

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class NudgeRepository(BaseRepository):
    """スマホ通知のCRUD"""

    async def get_nudge_config(self, user_id: int) -> dict | None:
        """通知設定を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM phone_nudges WHERE user_id = $1",
                user_id,
            )
        return dict(row) if row else None

    async def upsert_config(self, user_id: int, webhook_url: str, enabled: bool = True) -> None:
        """通知設定を作成/更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO phone_nudges (user_id, webhook_url, enabled)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE
                SET webhook_url = $2, enabled = $3
                """,
                user_id,
                webhook_url,
                enabled,
            )

    async def toggle_enabled(self, user_id: int, enabled: bool) -> bool:
        """通知のON/OFF切り替え"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE phone_nudges SET enabled = $2
                WHERE user_id = $1
                """,
                user_id,
                enabled,
            )
        return result != "UPDATE 0"

    async def add_history(self, user_id: int, event_type: str, message: str) -> None:
        """通知履歴を追加"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO nudge_history (user_id, event_type, message)
                VALUES ($1, $2, $3)
                """,
                user_id,
                event_type,
                message,
            )
