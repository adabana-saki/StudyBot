"""サンクチュアリ（癒しの学習庭園）DB操作"""

import logging

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class SanctuaryRepository(BaseRepository):
    """サンクチュアリのCRUD"""

    # --- 庭園 ---

    async def get_garden(self, user_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sanctuary_gardens WHERE user_id = $1",
                user_id,
            )
        return dict(row) if row else {}

    async def create_garden(self, user_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sanctuary_gardens (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING *
                """,
                user_id,
            )
            if not row:
                row = await conn.fetchrow(
                    "SELECT * FROM sanctuary_gardens WHERE user_id = $1",
                    user_id,
                )
        return dict(row) if row else {}

    async def update_garden(
        self, user_id: int, vitality: float, harmony: float, season: str
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sanctuary_gardens
                SET vitality = $2, harmony = $3, season = $4,
                    updated_at = NOW()
                WHERE user_id = $1
                """,
                user_id,
                vitality,
                harmony,
                season,
            )

    async def update_garden_last_tended(self, user_id: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sanctuary_gardens
                SET last_tended_at = NOW(), updated_at = NOW()
                WHERE user_id = $1
                """,
                user_id,
            )

    # --- 植物 ---

    async def get_plants(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM sanctuary_plants
                WHERE user_id = $1
                ORDER BY planted_at
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def get_plant(self, plant_id: int, user_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sanctuary_plants WHERE id = $1 AND user_id = $2",
                plant_id,
                user_id,
            )
        return dict(row) if row else {}

    async def plant_seed(self, user_id: int, plant_type: str, name: str) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sanctuary_plants (user_id, plant_type, name)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                user_id,
                plant_type,
                name,
            )
        return dict(row) if row else {}

    async def update_plant(self, plant_id: int, growth: float, health: float) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sanctuary_plants
                SET growth = $2, health = $3, updated_at = NOW()
                WHERE id = $1
                """,
                plant_id,
                growth,
                health,
            )

    async def decay_plants(self, hours_threshold: int) -> int:
        """長時間放置された植物の健康度を減衰させる"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE sanctuary_plants
                SET health = GREATEST(0, health - 5),
                    updated_at = NOW()
                WHERE health > 0
                  AND updated_at < NOW() - INTERVAL '1 hour' * $1
                """,
                hours_threshold,
            )
        count = int(result.split()[-1]) if result else 0
        return count

    async def count_plants(self, user_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM sanctuary_plants WHERE user_id = $1",
                user_id,
            )

    # --- セッション ---

    async def create_session(
        self,
        user_id: int,
        phase: str,
        mood_before: int,
        energy_before: int,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sanctuary_sessions
                    (user_id, phase, mood_before, energy_before)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                user_id,
                phase,
                mood_before,
                energy_before,
            )
        return dict(row) if row else {}

    async def get_active_session(self, user_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM sanctuary_sessions
                WHERE user_id = $1 AND completed = FALSE
                ORDER BY started_at DESC LIMIT 1
                """,
                user_id,
            )
        return dict(row) if row else {}

    async def complete_session(
        self,
        session_id: int,
        mood_after: int,
        energy_after: int,
        growth_points: float,
        note: str,
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sanctuary_sessions
                SET mood_after = $2, energy_after = $3,
                    growth_points = $4, note = $5,
                    completed = TRUE, completed_at = NOW()
                WHERE id = $1
                """,
                session_id,
                mood_after,
                energy_after,
                growth_points,
                note,
            )

    async def get_sessions_today(self, user_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*) FROM sanctuary_sessions
                WHERE user_id = $1
                  AND started_at::date = CURRENT_DATE
                  AND completed = TRUE
                """,
                user_id,
            )

    async def had_session_yesterday(self, user_id: int) -> bool:
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM sanctuary_sessions
                WHERE user_id = $1
                  AND started_at::date = CURRENT_DATE - 1
                  AND completed = TRUE
                """,
                user_id,
            )
        return count > 0

    async def get_session_stats(self, user_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(growth_points), 0) as total_growth,
                    COALESCE(AVG(mood_after - mood_before), 0) as avg_mood_change,
                    COALESCE(AVG(growth_points), 0) as avg_growth
                FROM sanctuary_sessions
                WHERE user_id = $1 AND completed = TRUE
                """,
                user_id,
            )
        return dict(row) if row else {}

    async def get_all_gardens(self) -> list[dict]:
        """全庭園を取得（日次更新用）"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM sanctuary_gardens")
        return [dict(r) for r in rows]
