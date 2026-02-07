"""スタディレイド DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class RaidRepository(BaseRepository):
    """スタディレイド関連のCRUD"""

    async def create_raid(
        self,
        creator_id: int,
        guild_id: int,
        channel_id: int,
        topic: str,
        duration_minutes: int,
        max_participants: int,
    ) -> dict:
        """レイドを作成"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO study_raids
                    (creator_id, guild_id, channel_id, topic,
                     duration_minutes, max_participants, state, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, 'recruiting', $7)
                RETURNING *
                """,
                creator_id,
                guild_id,
                channel_id,
                topic,
                duration_minutes,
                max_participants,
                datetime.now(UTC),
            )
        return dict(row)

    async def add_participant(self, raid_id: int, user_id: int) -> bool:
        """参加者を追加（既に参加済みならFalse）"""
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO raid_participants (raid_id, user_id, joined_at)
                    VALUES ($1, $2, $3)
                    """,
                    raid_id,
                    user_id,
                    datetime.now(UTC),
                )
                return True
            except Exception:
                # UNIQUE制約違反 = 既に参加済み
                return False

    async def remove_participant(self, raid_id: int, user_id: int) -> bool:
        """参加者を削除"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM raid_participants
                WHERE raid_id = $1 AND user_id = $2
                """,
                raid_id,
                user_id,
            )
        return result != "DELETE 0"

    async def get_active_raids(self, guild_id: int) -> list[dict]:
        """ギルドのアクティブなレイドを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sr.*, u.username as creator_name
                FROM study_raids sr
                JOIN users u ON u.user_id = sr.creator_id
                WHERE sr.guild_id = $1 AND sr.state IN ('recruiting', 'active')
                ORDER BY sr.created_at DESC
                """,
                guild_id,
            )
        return [dict(row) for row in rows]

    async def get_raid(self, raid_id: int) -> dict | None:
        """レイド情報を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM study_raids WHERE id = $1",
                raid_id,
            )
        return dict(row) if row else None

    async def get_participants(self, raid_id: int) -> list[dict]:
        """レイド参加者一覧を取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT rp.*, u.username
                FROM raid_participants rp
                JOIN users u ON u.user_id = rp.user_id
                WHERE rp.raid_id = $1
                ORDER BY rp.joined_at
                """,
                raid_id,
            )
        return [dict(row) for row in rows]

    async def start_raid(self, raid_id: int) -> None:
        """レイドを開始状態に更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE study_raids
                SET state = 'active', started_at = $2
                WHERE id = $1
                """,
                raid_id,
                datetime.now(UTC),
            )

    async def complete_raid(self, raid_id: int) -> None:
        """レイドを完了状態に更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE study_raids
                SET state = 'completed', ended_at = $2
                WHERE id = $1
                """,
                raid_id,
                datetime.now(UTC),
            )

    async def mark_participant_completed(self, raid_id: int, user_id: int) -> None:
        """参加者を完了にマーク"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE raid_participants
                SET completed = true
                WHERE raid_id = $1 AND user_id = $2
                """,
                raid_id,
                user_id,
            )

    async def get_participant_count(self, raid_id: int) -> int:
        """レイドの参加者数を取得"""
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM raid_participants WHERE raid_id = $1",
                raid_id,
            )
        return count or 0
