"""スタディルーム リポジトリ"""

import logging
from datetime import datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class RoomRepository(BaseRepository):
    """study_rooms / room_members / room_history テーブル操作"""

    async def create_room(
        self,
        guild_id: int,
        name: str,
        theme: str = "general",
        vc_channel_id: int | None = None,
        collective_goal_minutes: int = 0,
        max_occupants: int = 20,
        created_by: int | None = None,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO study_rooms
                    (guild_id, name, theme, vc_channel_id,
                     collective_goal_minutes, max_occupants, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                guild_id, name, theme, vc_channel_id,
                collective_goal_minutes, max_occupants, created_by,
            )
            return dict(row) if row else {}

    async def get_room(self, room_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT r.*,
                       (SELECT COUNT(*) FROM room_members WHERE room_id = r.id)
                           AS member_count
                FROM study_rooms r
                WHERE r.id = $1
                """,
                room_id,
            )
            return dict(row) if row else None

    async def get_guild_rooms(self, guild_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.*,
                       (SELECT COUNT(*) FROM room_members WHERE room_id = r.id)
                           AS member_count
                FROM study_rooms r
                WHERE r.guild_id = $1
                  AND r.state = 'active'
                ORDER BY r.created_at DESC
                """,
                guild_id,
            )
            return [dict(r) for r in rows]

    async def join_room(
        self, room_id: int, user_id: int, platform: str, topic: str = ""
    ) -> bool:
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO room_members (room_id, user_id, platform, topic)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (room_id, user_id) DO UPDATE
                        SET platform = $3, topic = $4, joined_at = NOW()
                    """,
                    room_id, user_id, platform, topic,
                )
                return True
            except Exception:
                logger.debug("ルーム参加失敗", exc_info=True)
                return False

    async def leave_room(self, room_id: int, user_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            member = await conn.fetchrow(
                "SELECT * FROM room_members WHERE room_id = $1 AND user_id = $2",
                room_id, user_id,
            )
            if not member:
                return None

            await conn.execute(
                "DELETE FROM room_members WHERE room_id = $1 AND user_id = $2",
                room_id, user_id,
            )
            return dict(member)

    async def get_room_members(self, room_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT rm.user_id, u.username, rm.platform,
                       rm.topic, rm.joined_at
                FROM room_members rm
                JOIN users u ON u.user_id = rm.user_id
                WHERE rm.room_id = $1
                ORDER BY rm.joined_at
                """,
                room_id,
            )
            return [dict(r) for r in rows]

    async def update_collective_progress(
        self, room_id: int, delta: int
    ) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE study_rooms
                SET collective_progress_minutes =
                    collective_progress_minutes + $2
                WHERE id = $1
                RETURNING collective_goal_minutes, collective_progress_minutes
                """,
                room_id, delta,
            )
            return dict(row) if row else None

    async def get_room_by_vc_channel(self, vc_channel_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM study_rooms
                WHERE vc_channel_id = $1 AND state = 'active'
                """,
                vc_channel_id,
            )
            return dict(row) if row else None

    async def record_room_history(
        self,
        room_id: int,
        user_id: int,
        platform: str,
        joined_at: datetime,
        duration_minutes: int = 0,
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO room_history
                    (room_id, user_id, platform, joined_at, duration_minutes)
                VALUES ($1, $2, $3, $4, $5)
                """,
                room_id, user_id, platform, joined_at, duration_minutes,
            )

    async def get_user_room(self, user_id: int) -> dict | None:
        """ユーザーが現在参加しているルームを取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT rm.*, r.name AS room_name, r.guild_id
                FROM room_members rm
                JOIN study_rooms r ON r.id = rm.room_id
                WHERE rm.user_id = $1
                """,
                user_id,
            )
            return dict(row) if row else None
