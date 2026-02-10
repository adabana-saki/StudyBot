"""チャレンジリポジトリ"""

import logging
from datetime import date

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ChallengeRepository(BaseRepository):
    """challenges テーブル操作"""

    async def create_challenge(
        self,
        creator_id: int,
        guild_id: int,
        name: str,
        description: str,
        goal_type: str,
        goal_target: int,
        duration_days: int,
        start_date: date,
        end_date: date,
        xp_multiplier: float = 1.5,
    ) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO challenges
                    (creator_id, guild_id, name, description, goal_type,
                     goal_target, duration_days, start_date, end_date, xp_multiplier)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """,
                creator_id,
                guild_id,
                name,
                description,
                goal_type,
                goal_target,
                duration_days,
                start_date,
                end_date,
                xp_multiplier,
            )

    async def get_challenge(self, challenge_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT c.*, u.username AS creator_name,
                       (SELECT COUNT(*)
                        FROM challenge_participants
                        WHERE challenge_id = c.id) AS participant_count
                FROM challenges c
                JOIN users u ON u.user_id = c.creator_id
                WHERE c.id = $1
                """,
                challenge_id,
            )
            return dict(row) if row else None

    async def list_challenges(self, guild_id: int, status: str | None = None) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT c.*, u.username AS creator_name,
                       (SELECT COUNT(*)
                        FROM challenge_participants
                        WHERE challenge_id = c.id) AS participant_count
                FROM challenges c
                JOIN users u ON u.user_id = c.creator_id
                WHERE c.guild_id = $1
            """
            params: list = [guild_id]
            if status:
                params.append(status)
                query += f" AND c.status = ${len(params)}"
            query += " ORDER BY c.created_at DESC"
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def update_status(self, challenge_id: int, status: str) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE challenges SET status = $2 WHERE id = $1",
                challenge_id,
                status,
            )

    async def set_channel(self, challenge_id: int, channel_id: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE challenges SET channel_id = $2 WHERE id = $1",
                challenge_id,
                channel_id,
            )

    async def join_challenge(self, challenge_id: int, user_id: int) -> bool:
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO challenge_participants (challenge_id, user_id) VALUES ($1, $2)",
                    challenge_id,
                    user_id,
                )
                return True
            except Exception:
                logger.debug(
                    "チャレンジ参加失敗 (challenge=%d, user=%d)",
                    challenge_id,
                    user_id,
                    exc_info=True,
                )
                return False

    async def get_participant(self, challenge_id: int, user_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM challenge_participants WHERE challenge_id = $1 AND user_id = $2",
                challenge_id,
                user_id,
            )
            return dict(row) if row else None

    async def checkin(
        self,
        challenge_id: int,
        user_id: int,
        progress_delta: int,
        note: str = "",
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            today = date.today()
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO challenge_checkins
                        (challenge_id, user_id, checkin_date, progress_delta, note)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (challenge_id, user_id, checkin_date) DO UPDATE SET
                        progress_delta = challenge_checkins.progress_delta + $4
                    """,
                    challenge_id,
                    user_id,
                    today,
                    progress_delta,
                    note,
                )
                await conn.execute(
                    """
                    UPDATE challenge_participants
                    SET progress = progress + $3,
                        checkins = checkins + 1,
                        last_checkin_date = $4,
                        completed = (
                            progress + $3 >= (
                                SELECT goal_target
                                FROM challenges
                                WHERE id = $1
                            )
                        )
                    WHERE challenge_id = $1 AND user_id = $2
                    """,
                    challenge_id,
                    user_id,
                    progress_delta,
                    today,
                )
                row = await conn.fetchrow(
                    "SELECT * FROM challenge_participants WHERE challenge_id = $1 AND user_id = $2",
                    challenge_id,
                    user_id,
                )
                return dict(row) if row else {}

    async def get_leaderboard(self, challenge_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT cp.*, u.username
                FROM challenge_participants cp
                JOIN users u ON u.user_id = cp.user_id
                WHERE cp.challenge_id = $1
                ORDER BY cp.progress DESC, cp.checkins DESC
                """,
                challenge_id,
            )
            return [dict(r) for r in rows]

    async def get_active_challenge_multiplier(self, user_id: int) -> float | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT c.xp_multiplier FROM challenges c
                JOIN challenge_participants cp ON cp.challenge_id = c.id
                WHERE cp.user_id = $1 AND c.status = 'active'
                  AND c.start_date <= CURRENT_DATE
                  AND c.end_date >= CURRENT_DATE
                LIMIT 1
                """,
                user_id,
            )
            return row["xp_multiplier"] if row else None
