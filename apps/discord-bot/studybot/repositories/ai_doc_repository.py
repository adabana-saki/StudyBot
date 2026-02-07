"""AIドキュメント解析 DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AIDocRepository(BaseRepository):
    """AI要約キャッシュのCRUD"""

    async def get_cached_summary(
        self, file_hash: str, detail_level: str, summary_type: str
    ) -> str | None:
        """キャッシュされた要約を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT summary FROM ai_document_summaries
                WHERE file_hash = $1 AND detail_level = $2 AND summary_type = $3
                """,
                file_hash,
                detail_level,
                summary_type,
            )
        return row["summary"] if row else None

    async def save_summary(
        self,
        user_id: int,
        file_hash: str,
        detail_level: str,
        summary_type: str,
        summary: str,
    ) -> None:
        """要約をキャッシュに保存"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ai_document_summaries
                    (user_id, file_hash, detail_level, summary_type, summary)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (file_hash, detail_level, summary_type)
                DO UPDATE SET summary = $5, created_at = $6
                """,
                user_id,
                file_hash,
                detail_level,
                summary_type,
                summary,
                datetime.now(UTC),
            )

    async def get_daily_usage_count(self, user_id: int) -> int:
        """今日のAPI使用回数を取得"""
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM ai_document_summaries
                WHERE user_id = $1
                  AND created_at >= CURRENT_DATE
                """,
                user_id,
            )
        return count or 0
