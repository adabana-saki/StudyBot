"""エクスペディション（知識探検冒険）DB操作"""

import logging

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ExpeditionRepository(BaseRepository):
    """エクスペディションのCRUD"""

    # --- 探検家 ---

    async def get_explorer(self, user_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM expedition_explorers WHERE user_id = $1",
                user_id,
            )
        return dict(row) if row else {}

    async def create_explorer(self, user_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO expedition_explorers (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING *
                """,
                user_id,
            )
            if not row:
                row = await conn.fetchrow(
                    "SELECT * FROM expedition_explorers WHERE user_id = $1",
                    user_id,
                )
        return dict(row) if row else {}

    async def update_explorer(
        self, user_id: int, total_territories: int, total_points: int
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE expedition_explorers
                SET total_territories = $2, total_points = $3,
                    updated_at = NOW()
                WHERE user_id = $1
                """,
                user_id,
                total_territories,
                total_points,
            )

    # --- 領域マスタ ---

    async def get_territories(self, region: str = "") -> list[dict]:
        async with self.db_pool.acquire() as conn:
            if region:
                rows = await conn.fetch(
                    "SELECT * FROM expedition_territories WHERE region = $1 ORDER BY difficulty",
                    region,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM expedition_territories ORDER BY region, difficulty"
                )
        return [dict(r) for r in rows]

    async def get_territory(self, territory_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM expedition_territories WHERE id = $1",
                territory_id,
            )
        return dict(row) if row else {}

    async def get_territory_by_keyword(self, keyword: str) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM expedition_territories
                WHERE topic_keyword ILIKE $1
                LIMIT 1
                """,
                f"%{keyword}%",
            )
        return dict(row) if row else {}

    async def upsert_territory(
        self,
        name: str,
        region: str,
        topic_keyword: str,
        difficulty: int,
        required_minutes: int,
        emoji: str,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO expedition_territories
                    (name, region, topic_keyword, difficulty, required_minutes, emoji)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (topic_keyword) DO UPDATE
                    SET name = $1, region = $2, difficulty = $4,
                        required_minutes = $5, emoji = $6
                RETURNING *
                """,
                name,
                region,
                topic_keyword,
                difficulty,
                required_minutes,
                emoji,
            )
        return dict(row) if row else {}

    # --- 探索進捗 ---

    async def get_progress(self, user_id: int, territory_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM expedition_progress
                WHERE user_id = $1 AND territory_id = $2
                """,
                user_id,
                territory_id,
            )
        return dict(row) if row else {}

    async def get_all_progress(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT p.*, t.name as territory_name, t.region,
                       t.required_minutes, t.emoji, t.topic_keyword
                FROM expedition_progress p
                JOIN expedition_territories t ON t.id = p.territory_id
                WHERE p.user_id = $1
                ORDER BY t.region, t.difficulty
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def add_progress(self, user_id: int, territory_id: int, minutes: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO expedition_progress (user_id, territory_id, minutes_spent)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, territory_id)
                DO UPDATE SET minutes_spent = expedition_progress.minutes_spent + $3,
                             updated_at = NOW()
                RETURNING *
                """,
                user_id,
                territory_id,
                minutes,
            )
        return dict(row) if row else {}

    async def mark_completed(self, user_id: int, territory_id: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE expedition_progress
                SET completed = TRUE, completed_at = NOW()
                WHERE user_id = $1 AND territory_id = $2
                """,
                user_id,
                territory_id,
            )

    async def count_completed(self, user_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*) FROM expedition_progress
                WHERE user_id = $1 AND completed = TRUE
                """,
                user_id,
            )

    # --- パーティ ---

    async def create_party(
        self,
        creator_id: int,
        guild_id: int,
        name: str,
        region: str,
        goal_minutes: int,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO expedition_parties
                    (creator_id, guild_id, name, region, goal_minutes)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                creator_id,
                guild_id,
                name,
                region,
                goal_minutes,
            )
            # Add creator as member
            if row:
                await conn.execute(
                    """
                    INSERT INTO expedition_party_members (party_id, user_id)
                    VALUES ($1, $2)
                    """,
                    row["id"],
                    creator_id,
                )
        return dict(row) if row else {}

    async def get_party(self, party_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM expedition_parties WHERE id = $1",
                party_id,
            )
        return dict(row) if row else {}

    async def get_party_members(self, party_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM expedition_party_members
                WHERE party_id = $1
                ORDER BY joined_at
                """,
                party_id,
            )
        return [dict(r) for r in rows]

    async def join_party(self, party_id: int, user_id: int) -> bool:
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO expedition_party_members (party_id, user_id)
                    VALUES ($1, $2)
                    """,
                    party_id,
                    user_id,
                )
                return True
            except Exception:
                return False

    async def add_party_contribution(self, party_id: int, user_id: int, minutes: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE expedition_party_members
                SET contribution_minutes = contribution_minutes + $3
                WHERE party_id = $1 AND user_id = $2
                """,
                party_id,
                user_id,
                minutes,
            )
            await conn.execute(
                """
                UPDATE expedition_parties
                SET progress_minutes = progress_minutes + $2
                WHERE id = $1
                """,
                party_id,
                minutes,
            )

    async def get_user_active_party(self, user_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT p.* FROM expedition_parties p
                JOIN expedition_party_members m ON m.party_id = p.id
                WHERE m.user_id = $1 AND p.status = 'active'
                LIMIT 1
                """,
                user_id,
            )
        return dict(row) if row else {}

    async def complete_party(self, party_id: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE expedition_parties
                SET status = 'completed', completed_at = NOW()
                WHERE id = $1
                """,
                party_id,
            )

    async def get_active_parties(self, guild_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM expedition_parties
                WHERE guild_id = $1 AND status = 'active'
                ORDER BY created_at DESC
                """,
                guild_id,
            )
        return [dict(r) for r in rows]

    # --- 発見イベント ---

    async def create_discovery(
        self,
        guild_id: int,
        title: str,
        description: str,
        reward_points: int,
        expires_at: str,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO expedition_discoveries
                    (guild_id, title, description, reward_points, expires_at)
                VALUES ($1, $2, $3, $4, $5::timestamptz)
                RETURNING *
                """,
                guild_id,
                title,
                description,
                reward_points,
                expires_at,
            )
        return dict(row) if row else {}

    async def get_active_discovery(self, guild_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM expedition_discoveries
                WHERE guild_id = $1 AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
                """,
                guild_id,
            )
        return dict(row) if row else {}

    # --- 探検日誌 ---

    async def create_journal_entry(self, user_id: int, title: str, content: str) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO expedition_journal_entries
                    (user_id, title, content)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                user_id,
                title,
                content,
            )
        return dict(row) if row else {}

    async def get_journal_entries(self, user_id: int, limit: int = 5) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM expedition_journal_entries
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
        return [dict(r) for r in rows]

    async def count_journal_entries(self, user_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*) FROM expedition_journal_entries
                WHERE user_id = $1
                """,
                user_id,
            )
