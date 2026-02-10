"""デイリークエスト リポジトリ"""

import logging
from datetime import date

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class QuestRepository(BaseRepository):
    """daily_quests テーブル操作"""

    async def get_user_quests(self, user_id: int, quest_date: date) -> list[dict]:
        """指定日のユーザークエストを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM daily_quests
                WHERE user_id = $1 AND quest_date = $2
                ORDER BY id
                """,
                user_id,
                quest_date,
            )
            return [dict(r) for r in rows]

    async def create_quest(
        self,
        user_id: int,
        quest_type: str,
        target: int,
        reward_xp: int,
        reward_coins: int,
        quest_date: date,
    ) -> int:
        """クエストを作成"""
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO daily_quests
                    (user_id, quest_type, target, reward_xp, reward_coins, quest_date)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                user_id,
                quest_type,
                target,
                reward_xp,
                reward_coins,
                quest_date,
            )

    async def update_progress(
        self, user_id: int, quest_type: str, quest_date: date, delta: int
    ) -> list[dict]:
        """指定タイプのクエスト進捗を更新し、更新後のクエストを返す"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE daily_quests
                SET progress = LEAST(progress + $4, target),
                    completed = (progress + $4 >= target)
                WHERE user_id = $1
                  AND quest_type = $2
                  AND quest_date = $3
                  AND claimed = FALSE
                """,
                user_id,
                quest_type,
                quest_date,
                delta,
            )
            rows = await conn.fetch(
                """
                SELECT * FROM daily_quests
                WHERE user_id = $1 AND quest_type = $2 AND quest_date = $3
                """,
                user_id,
                quest_type,
                quest_date,
            )
            return [dict(r) for r in rows]

    async def claim_quest(self, quest_id: int, user_id: int) -> dict | None:
        """クエスト報酬を受け取る"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE daily_quests
                SET claimed = TRUE
                WHERE id = $1 AND user_id = $2
                  AND completed = TRUE AND claimed = FALSE
                RETURNING *
                """,
                quest_id,
                user_id,
            )
            return dict(row) if row else None

    async def get_quest_by_id(self, quest_id: int, user_id: int) -> dict | None:
        """IDでクエストを取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM daily_quests
                WHERE id = $1 AND user_id = $2
                """,
                quest_id,
                user_id,
            )
            return dict(row) if row else None

    async def get_user_activity_profile(self, user_id: int, days: int = 14) -> dict:
        """ユーザーの直近アクティビティプロファイルを取得（スマートクエスト用）"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    (SELECT COUNT(*) FROM pomodoro_sessions
                     WHERE user_id = $1 AND created_at >= NOW() - make_interval(days => $2)
                    ) AS pomodoro_count,
                    (SELECT COALESCE(SUM(duration_minutes), 0) FROM study_logs
                     WHERE user_id = $1 AND logged_at >= NOW() - make_interval(days => $2)
                    ) AS study_minutes,
                    (SELECT COUNT(*) FROM todos
                     WHERE user_id = $1 AND status = 'completed'
                       AND completed_at >= NOW() - make_interval(days => $2)
                    ) AS tasks_completed,
                    (SELECT COUNT(*) FROM study_logs
                     WHERE user_id = $1 AND logged_at >= NOW() - make_interval(days => $2)
                    ) AS log_count
                """,
                user_id,
                days,
            )
        return (
            dict(row)
            if row
            else {
                "pomodoro_count": 0,
                "study_minutes": 0,
                "tasks_completed": 0,
                "log_count": 0,
            }
        )

    async def get_consecutive_quest_days(self, user_id: int) -> int:
        """連続してデイリークエストを全完了した日数を取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT quest_date,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE completed) AS done
                FROM daily_quests
                WHERE user_id = $1
                GROUP BY quest_date
                ORDER BY quest_date DESC
                LIMIT 30
                """,
                user_id,
            )
        if not rows:
            return 0
        streak = 0
        from datetime import date as date_type
        from datetime import timedelta

        expected = date_type.today()
        for row in rows:
            qdate = row["quest_date"]
            if qdate == expected and row["done"] == row["total"]:
                streak += 1
                expected -= timedelta(days=1)
            else:
                break
        return streak
