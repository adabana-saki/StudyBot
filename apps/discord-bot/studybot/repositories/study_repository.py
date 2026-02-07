"""学習ログ & 統計 DB操作"""

import logging
from datetime import UTC, date, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class StudyRepository(BaseRepository):
    """学習ログ・統計のCRUD"""

    async def add_log(
        self,
        user_id: int,
        guild_id: int,
        duration_minutes: int,
        topic: str = "",
        source: str = "manual",
    ) -> int:
        """学習ログを追加"""
        async with self.db_pool.acquire() as conn:
            log_id = await conn.fetchval(
                """
                INSERT INTO study_logs (user_id, guild_id, topic, duration_minutes, source)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                user_id,
                guild_id,
                topic,
                duration_minutes,
                source,
            )
        return log_id

    async def get_user_stats(self, user_id: int, guild_id: int, days: int = 7) -> dict:
        """ユーザーの統計情報を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(duration_minutes), 0) AS total_minutes,
                    COUNT(*) AS session_count,
                    COALESCE(AVG(duration_minutes), 0) AS avg_minutes
                FROM study_logs
                WHERE user_id = $1 AND guild_id = $2
                  AND logged_at >= CURRENT_TIMESTAMP - ($3 || ' days')::interval
                """,
                user_id,
                guild_id,
                str(days),
            )
        return dict(row) if row else {"total_minutes": 0, "session_count": 0, "avg_minutes": 0}

    async def get_daily_totals(self, user_id: int, guild_id: int, days: int = 14) -> list[dict]:
        """日ごとの学習時間を取得（チャート用）"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    DATE(logged_at) AS study_date,
                    SUM(duration_minutes) AS total_minutes
                FROM study_logs
                WHERE user_id = $1 AND guild_id = $2
                  AND logged_at >= CURRENT_TIMESTAMP - ($3 || ' days')::interval
                GROUP BY DATE(logged_at)
                ORDER BY study_date
                """,
                user_id,
                guild_id,
                str(days),
            )
        return [dict(row) for row in rows]

    async def get_topic_breakdown(self, user_id: int, guild_id: int, days: int = 30) -> list[dict]:
        """トピック別の学習時間を取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    COALESCE(NULLIF(topic, ''), '未分類') AS topic,
                    SUM(duration_minutes) AS total_minutes
                FROM study_logs
                WHERE user_id = $1 AND guild_id = $2
                  AND logged_at >= CURRENT_TIMESTAMP - ($3 || ' days')::interval
                GROUP BY COALESCE(NULLIF(topic, ''), '未分類')
                ORDER BY total_minutes DESC
                LIMIT 10
                """,
                user_id,
                guild_id,
                str(days),
            )
        return [dict(row) for row in rows]

    async def update_stats_cache(
        self,
        user_id: int,
        guild_id: int,
        period: str,
        period_start: date,
        minutes: int,
        sessions: int = 1,
        tasks: int = 0,
    ) -> None:
        """統計キャッシュを更新（UPSERT）"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_stats
                    (user_id, guild_id, period, period_start, total_minutes, session_count,
                     tasks_completed, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (user_id, guild_id, period, period_start)
                DO UPDATE SET
                    total_minutes = user_stats.total_minutes + $5,
                    session_count = user_stats.session_count + $6,
                    tasks_completed = user_stats.tasks_completed + $7,
                    updated_at = $8
                """,
                user_id,
                guild_id,
                period,
                period_start,
                minutes,
                sessions,
                tasks,
                datetime.now(UTC),
            )

    async def get_guild_ranking(self, guild_id: int, days: int = 7, limit: int = 10) -> list[dict]:
        """サーバー内ランキングを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    sl.user_id,
                    u.username,
                    SUM(sl.duration_minutes) AS total_minutes,
                    COUNT(*) AS session_count
                FROM study_logs sl
                JOIN users u ON u.user_id = sl.user_id
                WHERE sl.guild_id = $1
                  AND sl.logged_at >= CURRENT_TIMESTAMP - ($2 || ' days')::interval
                GROUP BY sl.user_id, u.username
                ORDER BY total_minutes DESC
                LIMIT $3
                """,
                guild_id,
                str(days),
                limit,
            )
        return [dict(row) for row in rows]
