"""インサイトリポジトリ"""

import json
import logging
from datetime import date

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class InsightsRepository(BaseRepository):
    """weekly_reports + user_insights テーブル操作"""

    async def get_weekly_study_data(self, user_id: int, days: int = 7) -> dict:
        """過去N日分の学習データを集計"""
        async with self.db_pool.acquire() as conn:
            study_logs = await conn.fetch(
                """
                SELECT topic, duration_minutes, source, logged_at
                FROM study_logs WHERE user_id = $1
                AND logged_at >= NOW() - INTERVAL '1 day' * $2
                ORDER BY logged_at
                """,
                user_id,
                days,
            )

            pomodoro_sessions = await conn.fetch(
                """
                SELECT topic, work_minutes, total_work_seconds, started_at
                FROM pomodoro_sessions WHERE user_id = $1
                AND started_at >= NOW() - INTERVAL '1 day' * $2
                AND state = 'completed'
                """,
                user_id,
                days,
            )

            wellness_logs = await conn.fetch(
                """
                SELECT mood, energy, stress, logged_at
                FROM wellness_logs WHERE user_id = $1
                AND logged_at >= NOW() - INTERVAL '1 day' * $2
                ORDER BY logged_at
                """,
                user_id,
                days,
            )

            todos = await conn.fetch(
                """
                SELECT title, priority, status, deadline, completed_at, created_at
                FROM todos WHERE user_id = $1
                AND created_at >= NOW() - INTERVAL '1 day' * $2
                """,
                user_id,
                days,
            )

            flashcard_reviews = await conn.fetch(
                """
                SELECT fr.quality, fr.reviewed_at
                FROM flashcard_reviews fr
                WHERE fr.user_id = $1
                AND fr.reviewed_at >= NOW() - INTERVAL '1 day' * $2
                """,
                user_id,
                days,
            )

            focus_sessions = await conn.fetch(
                """
                SELECT duration_minutes, state, started_at, ended_at
                FROM focus_sessions WHERE user_id = $1
                AND started_at >= NOW() - INTERVAL '1 day' * $2
                """,
                user_id,
                days,
            )

        return {
            "study_logs": [dict(r) for r in study_logs],
            "pomodoro_sessions": [dict(r) for r in pomodoro_sessions],
            "wellness_logs": [dict(r) for r in wellness_logs],
            "todos": [dict(r) for r in todos],
            "flashcard_reviews": [dict(r) for r in flashcard_reviews],
            "focus_sessions": [dict(r) for r in focus_sessions],
        }

    async def save_report(
        self,
        user_id: int,
        week_start: date,
        week_end: date,
        raw_data: dict,
        insights: list,
        summary: str,
    ) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO weekly_reports
                    (user_id, week_start, week_end, raw_data, insights, summary)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, week_start) DO UPDATE SET
                    raw_data = $4, insights = $5, summary = $6, generated_at = NOW()
                RETURNING id
                """,
                user_id,
                week_start,
                week_end,
                json.dumps(raw_data, default=str),
                json.dumps(insights, default=str),
                summary,
            )

    async def save_insights(self, user_id: int, insights: list[dict]) -> None:
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 古いインサイトを非アクティブに
                await conn.execute(
                    "UPDATE user_insights SET active = FALSE WHERE user_id = $1",
                    user_id,
                )
                if insights:
                    # バッチINSERT（N+1 → 1クエリ）
                    await conn.executemany(
                        """
                        INSERT INTO user_insights
                            (user_id, insight_type, title, body, data, confidence)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        [
                            (
                                user_id,
                                ins.get("type", "general"),
                                ins.get("title", ""),
                                ins.get("body", ""),
                                json.dumps(ins.get("data", {})),
                                ins.get("confidence", 0.5),
                            )
                            for ins in insights
                        ],
                    )

    async def get_user_insights(self, user_id: int, active_only: bool = True) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            query = "SELECT * FROM user_insights WHERE user_id = $1"
            if active_only:
                query += " AND active = TRUE"
            query += " ORDER BY generated_at DESC LIMIT 20"
            rows = await conn.fetch(query, user_id)
            return [dict(r) for r in rows]

    async def get_reports(self, user_id: int, limit: int = 10) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, week_start, week_end, summary,
                       insights, generated_at, sent_via_dm
                FROM weekly_reports WHERE user_id = $1
                ORDER BY week_start DESC LIMIT $2
                """,
                user_id,
                limit,
            )
            return [dict(r) for r in rows]

    async def get_report(self, report_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM weekly_reports WHERE id = $1", report_id)
            return dict(row) if row else None

    async def mark_dm_sent(self, report_id: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE weekly_reports SET sent_via_dm = TRUE WHERE id = $1",
                report_id,
            )

    async def get_active_user_ids(self, days: int = 7) -> list[int]:
        """過去N日間にアクティブだったユーザーIDを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT user_id FROM study_logs
                WHERE logged_at >= NOW() - INTERVAL '1 day' * $1
                UNION
                SELECT DISTINCT user_id FROM pomodoro_sessions
                WHERE started_at >= NOW() - INTERVAL '1 day' * $1
                """,
                days,
            )
            return [r["user_id"] for r in rows]
