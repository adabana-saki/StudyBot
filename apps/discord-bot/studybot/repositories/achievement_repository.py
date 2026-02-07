"""実績システム DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AchievementRepository(BaseRepository):
    """実績関連のCRUD"""

    async def get_all_achievements(self) -> list[dict]:
        """全実績を取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM achievements ORDER BY category, target_value")
        return [dict(row) for row in rows]

    async def get_user_achievements(self, user_id: int) -> list[dict]:
        """ユーザーの実績進捗を取得（全実績とLEFT JOIN）"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.id, a.key, a.name, a.description, a.emoji,
                       a.category, a.target_value, a.reward_coins,
                       COALESCE(ua.progress, 0) as progress,
                       COALESCE(ua.unlocked, false) as unlocked,
                       ua.unlocked_at
                FROM achievements a
                LEFT JOIN user_achievements ua
                    ON ua.achievement_id = a.id AND ua.user_id = $1
                ORDER BY a.category, a.target_value
                """,
                user_id,
            )
        return [dict(row) for row in rows]

    async def get_user_progress(self, user_id: int, achievement_key: str) -> dict | None:
        """特定の実績のユーザー進捗を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT ua.*, a.key, a.name, a.target_value, a.reward_coins, a.emoji
                FROM user_achievements ua
                JOIN achievements a ON a.id = ua.achievement_id
                WHERE ua.user_id = $1 AND a.key = $2
                """,
                user_id,
                achievement_key,
            )
        return dict(row) if row else None

    async def update_progress(self, user_id: int, achievement_id: int, progress: int) -> None:
        """実績進捗をUPSERT"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_id, progress)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, achievement_id)
                DO UPDATE SET progress = $3
                """,
                user_id,
                achievement_id,
                progress,
            )

    async def unlock_achievement(self, user_id: int, achievement_id: int) -> None:
        """実績をアンロック"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_achievements
                SET unlocked = true, unlocked_at = $3
                WHERE user_id = $1 AND achievement_id = $2
                """,
                user_id,
                achievement_id,
                datetime.now(UTC),
            )

    async def get_achievement_by_key(self, key: str) -> dict | None:
        """キーで実績を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM achievements WHERE key = $1",
                key,
            )
        return dict(row) if row else None
