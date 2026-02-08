"""バディリポジトリ"""

import logging

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class BuddyRepository(BaseRepository):
    """buddy テーブル操作"""

    async def get_profile(self, user_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM buddy_profiles WHERE user_id = $1", user_id)
            return dict(row) if row else None

    async def upsert_profile(
        self, user_id: int, subjects: list[str], preferred_times: list[str], study_style: str
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO buddy_profiles (user_id, subjects, preferred_times, study_style)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE SET
                    subjects = $2, preferred_times = $3,
                    study_style = $4, updated_at = NOW()
                """,
                user_id,
                subjects,
                preferred_times,
                study_style,
            )

    async def find_compatible(
        self, user_id: int, guild_id: int, subject: str | None = None
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT bp.*, u.username FROM buddy_profiles bp
                JOIN users u ON u.user_id = bp.user_id
                WHERE bp.user_id != $1 AND bp.active = TRUE
            """
            params: list = [user_id]
            if subject:
                params.append(subject)
                query += f" AND ${len(params)} = ANY(bp.subjects)"
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def create_match(
        self, user_a: int, user_b: int, guild_id: int, subject: str | None, score: float
    ) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO buddy_matches
                    (user_a, user_b, guild_id, subject, compatibility_score, status)
                VALUES ($1, $2, $3, $4, $5, 'active')
                RETURNING id
                """,
                user_a,
                user_b,
                guild_id,
                subject,
                score,
            )

    async def get_active_matches(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT bm.*, u_a.username AS username_a, u_b.username AS username_b
                FROM buddy_matches bm
                JOIN users u_a ON u_a.user_id = bm.user_a
                JOIN users u_b ON u_b.user_id = bm.user_b
                WHERE (bm.user_a = $1 OR bm.user_b = $1) AND bm.status = 'active'
                ORDER BY bm.matched_at DESC
                """,
                user_id,
            )
            return [dict(r) for r in rows]

    async def get_match_history(self, user_id: int, limit: int = 20) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT bm.*, u_a.username AS username_a, u_b.username AS username_b
                FROM buddy_matches bm
                JOIN users u_a ON u_a.user_id = bm.user_a
                JOIN users u_b ON u_b.user_id = bm.user_b
                WHERE bm.user_a = $1 OR bm.user_b = $1
                ORDER BY bm.matched_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
            return [dict(r) for r in rows]

    async def end_match(self, match_id: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE buddy_matches SET status = 'ended', ended_at = NOW() WHERE id = $1",
                match_id,
            )

    async def create_session(self, match_id: int, vc_channel_id: int | None = None) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO buddy_sessions (match_id, vc_channel_id)
                VALUES ($1, $2)
                RETURNING id
                """,
                match_id,
                vc_channel_id,
            )

    async def end_session(self, session_id: int, total_minutes: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE buddy_sessions SET ended_at = NOW(), total_minutes = $2
                WHERE id = $1
                """,
                session_id,
                total_minutes,
            )
