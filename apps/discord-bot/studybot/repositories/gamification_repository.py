"""ゲーミフィケーション DB操作"""

import logging
from datetime import UTC, date, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class GamificationRepository(BaseRepository):
    """XP・レベル関連のCRUD"""

    async def get_user_level(self, user_id: int) -> dict | None:
        """ユーザーレベル情報を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_levels WHERE user_id = $1",
                user_id,
            )
        return dict(row) if row else None

    async def ensure_user_level(self, user_id: int) -> dict:
        """ユーザーレベルレコードを確保（なければ作成）"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO user_levels (user_id, xp, level, streak_days)
                VALUES ($1, 0, 1, 0)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING *
                """,
                user_id,
            )
            if not row:
                row = await conn.fetchrow(
                    "SELECT * FROM user_levels WHERE user_id = $1",
                    user_id,
                )
        return dict(row)

    async def add_xp(self, user_id: int, amount: int, reason: str) -> dict:
        """XPを付与し、新しいレベル情報を返す"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # XPトランザクション記録
                await conn.execute(
                    """
                    INSERT INTO xp_transactions (user_id, amount, reason)
                    VALUES ($1, $2, $3)
                    """,
                    user_id,
                    amount,
                    reason,
                )

                # XP更新
                row = await conn.fetchrow(
                    """
                    UPDATE user_levels
                    SET xp = xp + $2, updated_at = $3
                    WHERE user_id = $1
                    RETURNING *
                    """,
                    user_id,
                    amount,
                    datetime.now(UTC),
                )

        return dict(row) if row else {}

    async def update_level(self, user_id: int, new_level: int) -> None:
        """レベルを更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_levels
                SET level = $2, updated_at = $3
                WHERE user_id = $1
                """,
                user_id,
                new_level,
                datetime.now(UTC),
            )

    async def update_streak(self, user_id: int, streak_days: int, study_date: date) -> None:
        """連続学習日数を更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_levels
                SET streak_days = $2, last_study_date = $3, updated_at = $4
                WHERE user_id = $1
                """,
                user_id,
                streak_days,
                study_date,
                datetime.now(UTC),
            )

    async def get_milestone(self, level: int) -> dict | None:
        """レベルマイルストーンを取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM level_milestones WHERE level = $1",
                level,
            )
        return dict(row) if row else None

    async def get_xp_ranking(self, guild_id: int, limit: int = 10) -> list[dict]:
        """XPランキングを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ul.user_id, u.username, ul.xp, ul.level, ul.streak_days
                FROM user_levels ul
                JOIN users u ON u.user_id = ul.user_id
                ORDER BY ul.xp DESC
                LIMIT $1
                """,
                limit,
            )
        return [dict(row) for row in rows]

    async def get_challenge_xp_multiplier(self, user_id: int) -> float | None:
        """アクティブチャレンジのXP乗算器を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT c.xp_multiplier FROM challenges c
                JOIN challenge_participants cp ON cp.challenge_id = c.id
                WHERE cp.user_id = $1 AND c.status = 'active'
                  AND c.start_date <= CURRENT_DATE AND c.end_date >= CURRENT_DATE
                LIMIT 1
                """,
                user_id,
            )
        return row["xp_multiplier"] if row else None

    async def get_user_rank(self, user_id: int) -> int:
        """ユーザーのXPランクを取得"""
        async with self.db_pool.acquire() as conn:
            rank = await conn.fetchval(
                """
                SELECT COUNT(*) + 1
                FROM user_levels
                WHERE xp > (SELECT COALESCE(xp, 0) FROM user_levels WHERE user_id = $1)
                """,
                user_id,
            )
        return rank or 0

    async def get_streak_details(self, user_id: int) -> dict | None:
        """連続学習の詳細情報を取得（現在のストリーク、最高記録）"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT streak_days, last_study_date,
                       COALESCE(best_streak, streak_days) AS best_streak
                FROM user_levels
                WHERE user_id = $1
                """,
                user_id,
            )
        if not row:
            return None
        return {
            "streak_days": row["streak_days"],
            "last_study_date": row["last_study_date"],
            "best_streak": row["best_streak"],
        }

    async def get_users_needing_streak_reminder(self, today: date) -> list[dict]:
        """今日まだ学習していないがストリーク>=3のユーザーを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ul.user_id, ul.streak_days
                FROM user_levels ul
                WHERE ul.streak_days >= 3
                  AND (ul.last_study_date IS NULL OR ul.last_study_date < $1)
                """,
                today,
            )
        return [dict(row) for row in rows]

    async def get_daily_top_earners(self, limit: int = 5) -> list[dict]:
        """本日のXP獲得量トップユーザーを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT xt.user_id, u.username,
                       SUM(xt.amount) AS daily_xp
                FROM xp_transactions xt
                JOIN users u ON u.user_id = xt.user_id
                WHERE xt.created_at >= CURRENT_DATE
                GROUP BY xt.user_id, u.username
                ORDER BY daily_xp DESC
                LIMIT $1
                """,
                limit,
            )
        return [dict(row) for row in rows]
