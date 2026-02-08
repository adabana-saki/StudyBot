"""スマホ通知 DB操作"""

import logging
from datetime import date, timedelta

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

    async def create_lock_session(
        self,
        user_id: int,
        lock_type: str,
        duration_minutes: int,
        coins_bet: int = 0,
        unlock_level: int = 1,
    ) -> dict:
        """ロックセッションを作成"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO phone_lock_sessions
                    (user_id, lock_type, duration_minutes, coins_bet,
                     unlock_level, state, started_at)
                VALUES ($1, $2, $3, $4, $5, 'active', NOW())
                RETURNING *
                """,
                user_id,
                lock_type,
                duration_minutes,
                coins_bet,
                unlock_level,
            )
        return dict(row)

    async def get_active_lock(self, user_id: int) -> dict | None:
        """アクティブなロックセッションを取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM phone_lock_sessions
                WHERE user_id = $1 AND state = 'active'
                ORDER BY started_at DESC
                LIMIT 1
                """,
                user_id,
            )
        return dict(row) if row else None

    async def complete_lock(self, session_id: int) -> dict | None:
        """ロックセッションを完了に更新"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE phone_lock_sessions
                SET state = 'completed', ended_at = NOW()
                WHERE id = $1
                RETURNING *
                """,
                session_id,
            )
        return dict(row) if row else None

    async def break_lock(self, session_id: int) -> dict | None:
        """ロックセッションを中断に更新"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE phone_lock_sessions
                SET state = 'broken', ended_at = NOW()
                WHERE id = $1
                RETURNING *
                """,
                session_id,
            )
        return dict(row) if row else None

    # --- 離脱検知DM ---

    async def record_churn_dm(self, user_id: int) -> None:
        """離脱検知DM送信を記録"""
        await self.add_history(user_id, "churn_detection", "離脱検知DMを送信")

    async def has_recent_churn_dm(self, user_id: int, days: int = 7) -> bool:
        """直近N日以内に離脱検知DMを送信済みか確認"""
        cutoff = date.today() - timedelta(days=days)
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM nudge_history
                WHERE user_id = $1
                  AND event_type = 'churn_detection'
                  AND sent_at >= $2
                """,
                user_id,
                cutoff,
            )
        return count > 0
