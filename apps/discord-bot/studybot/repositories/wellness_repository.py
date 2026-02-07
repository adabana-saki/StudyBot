"""ウェルネスログ DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class WellnessRepository(BaseRepository):
    """ウェルネスログのCRUD"""

    async def log_wellness(
        self,
        user_id: int,
        mood: int,
        energy: int,
        stress: int,
        note: str = "",
    ) -> dict:
        """ウェルネスログを記録"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO wellness_logs (user_id, mood, energy, stress, note, logged_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                user_id,
                mood,
                energy,
                stress,
                note,
                datetime.now(UTC),
            )
        return dict(row)

    async def get_recent_logs(self, user_id: int, days: int = 7) -> list[dict]:
        """直近のウェルネスログを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM wellness_logs
                WHERE user_id = $1
                  AND logged_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
                ORDER BY logged_at DESC
                """,
                user_id,
                days,
            )
        return [dict(row) for row in rows]

    async def get_averages(self, user_id: int, days: int = 7) -> dict | None:
        """期間内の平均値を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    AVG(mood) AS avg_mood,
                    AVG(energy) AS avg_energy,
                    AVG(stress) AS avg_stress,
                    COUNT(*) AS log_count
                FROM wellness_logs
                WHERE user_id = $1
                  AND logged_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
                """,
                user_id,
                days,
            )
        if row and row["log_count"] > 0:
            return dict(row)
        return None

    async def get_daily_averages(self, user_id: int, days: int = 14) -> list[dict]:
        """日別平均値を取得（トレンドチャート用）"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    DATE(logged_at) AS day,
                    AVG(mood) AS avg_mood,
                    AVG(energy) AS avg_energy,
                    AVG(stress) AS avg_stress
                FROM wellness_logs
                WHERE user_id = $1
                  AND logged_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
                GROUP BY DATE(logged_at)
                ORDER BY day
                """,
                user_id,
                days,
            )
        return [dict(row) for row in rows]

    async def get_today_log(self, user_id: int) -> dict | None:
        """今日のログが既にあるかチェック"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM wellness_logs
                WHERE user_id = $1
                  AND DATE(logged_at) = CURRENT_DATE
                ORDER BY logged_at DESC
                LIMIT 1
                """,
                user_id,
            )
        return dict(row) if row else None
