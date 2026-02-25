"""ゲーミフィケーション DB操作"""

import logging
from datetime import UTC, date, datetime, timedelta

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

    # --- 離脱検知 ---

    async def get_churned_users(self, min_streak: int = 10, inactive_days: int = 2) -> list[dict]:
        """ストリーク後に学習が途絶えたユーザーを取得"""
        cutoff = date.today() - timedelta(days=inactive_days)
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, streak_days,
                       COALESCE(best_streak, streak_days) AS best_streak,
                       last_study_date
                FROM user_levels
                WHERE last_study_date <= $1
                  AND COALESCE(best_streak, streak_days) >= $2
                """,
                cutoff,
                min_streak,
            )
        return [dict(row) for row in rows]

    # --- フォーカススコア ---

    async def get_focus_score_data(self, user_id: int, days: int = 14) -> dict:
        """フォーカススコア計算用データを取得"""
        async with self.db_pool.acquire() as conn:
            cutoff = datetime.now(UTC) - timedelta(days=days)

            # ポモドーロ完了率
            pomo = await conn.fetchrow(
                """
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE state = 'completed') AS completed
                FROM pomodoro_sessions
                WHERE user_id = $1 AND created_at >= $2
                """,
                user_id,
                cutoff,
            )

            # フォーカスセッション完了率
            focus = await conn.fetchrow(
                """
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE state = 'completed') AS completed
                FROM focus_sessions
                WHERE user_id = $1 AND started_at >= $2
                """,
                user_id,
                cutoff,
            )

            # フォーカスロック成功率
            lock = await conn.fetchrow(
                """
                SELECT COUNT(*) FILTER (WHERE state = 'completed') AS completed,
                       COUNT(*) FILTER (WHERE state IN ('completed', 'broken')) AS total
                FROM phone_lock_sessions
                WHERE user_id = $1 AND started_at >= $2
                """,
                user_id,
                cutoff,
            )

            # 学習一貫性 (過去N日のうち学習した日数)
            consistency = await conn.fetchrow(
                """
                SELECT COUNT(DISTINCT DATE(logged_at)) AS study_days
                FROM study_logs
                WHERE user_id = $1 AND logged_at >= $2
                """,
                user_id,
                cutoff,
            )

            # AppGuard: ブリーチ回数 & 監視対象セッション数
            breach_data = await conn.fetchrow(
                """
                SELECT COUNT(*) AS breach_count
                FROM app_breach_events
                WHERE user_id = $1 AND occurred_at >= $2
                """,
                user_id,
                cutoff,
            )

            monitored_sessions = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT session_id)
                FROM app_breach_events
                WHERE user_id = $1 AND occurred_at >= $2
                """,
                user_id,
                cutoff,
            ) or 0

        pomo_total = pomo["total"] if pomo else 0
        focus_total = focus["total"] if focus else 0
        session_total = pomo_total + focus_total
        session_completed = (pomo["completed"] if pomo else 0) + (
            focus["completed"] if focus else 0
        )

        return {
            "session_total": session_total,
            "session_completed": session_completed,
            "lock_total": lock["total"] if lock else 0,
            "lock_completed": lock["completed"] if lock else 0,
            "study_days": consistency["study_days"] if consistency else 0,
            "period_days": days,
            "breach_count": breach_data["breach_count"] if breach_data else 0,
            "monitored_sessions": monitored_sessions,
        }

    # --- 自己ベスト ---

    async def update_personal_bests(
        self,
        user_id: int,
        streak: int | None = None,
        daily_minutes: int | None = None,
        weekly_minutes: int | None = None,
    ) -> dict:
        """自己ベストを更新（GREATESTで比較）。更新された項目を返す"""
        updated = {}
        async with self.db_pool.acquire() as conn:
            if streak is not None:
                result = await conn.execute(
                    """
                    UPDATE user_levels
                    SET best_streak = GREATEST(COALESCE(best_streak, 0), $2)
                    WHERE user_id = $1 AND COALESCE(best_streak, 0) < $2
                    """,
                    user_id,
                    streak,
                )
                if result != "UPDATE 0":
                    updated["best_streak"] = streak

            if daily_minutes is not None:
                result = await conn.execute(
                    """
                    UPDATE user_levels
                    SET best_daily_minutes = GREATEST(COALESCE(best_daily_minutes, 0), $2)
                    WHERE user_id = $1 AND COALESCE(best_daily_minutes, 0) < $2
                    """,
                    user_id,
                    daily_minutes,
                )
                if result != "UPDATE 0":
                    updated["best_daily_minutes"] = daily_minutes

            if weekly_minutes is not None:
                result = await conn.execute(
                    """
                    UPDATE user_levels
                    SET best_weekly_minutes = GREATEST(COALESCE(best_weekly_minutes, 0), $2)
                    WHERE user_id = $1 AND COALESCE(best_weekly_minutes, 0) < $2
                    """,
                    user_id,
                    weekly_minutes,
                )
                if result != "UPDATE 0":
                    updated["best_weekly_minutes"] = weekly_minutes

        return updated

    async def get_personal_bests(self, user_id: int) -> dict:
        """全自己ベスト記録を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(best_streak, 0) AS best_streak,
                       COALESCE(best_daily_minutes, 0) AS best_daily_minutes,
                       COALESCE(best_weekly_minutes, 0) AS best_weekly_minutes
                FROM user_levels
                WHERE user_id = $1
                """,
                user_id,
            )
        if not row:
            return {"best_streak": 0, "best_daily_minutes": 0, "best_weekly_minutes": 0}
        return dict(row)

    async def get_today_study_minutes(self, user_id: int) -> int:
        """今日の合計学習時間（分）を取得"""
        async with self.db_pool.acquire() as conn:
            val = await conn.fetchval(
                """
                SELECT COALESCE(SUM(duration_minutes), 0)
                FROM study_logs
                WHERE user_id = $1 AND logged_at >= CURRENT_DATE
                """,
                user_id,
            )
        return val or 0

    async def get_week_study_minutes(self, user_id: int) -> int:
        """今週の合計学習時間（分）を取得"""
        async with self.db_pool.acquire() as conn:
            val = await conn.fetchval(
                """
                SELECT COALESCE(SUM(duration_minutes), 0)
                FROM study_logs
                WHERE user_id = $1
                  AND logged_at >= date_trunc('week', CURRENT_DATE)
                """,
                user_id,
            )
        return val or 0

    # --- シーズンパス ---

    async def get_active_season(self) -> dict | None:
        """アクティブなシーズンを取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM season_passes
                WHERE status = 'active'
                  AND start_date <= CURRENT_DATE
                  AND end_date >= CURRENT_DATE
                ORDER BY start_date DESC
                LIMIT 1
                """
            )
            return dict(row) if row else None

    async def create_season(self, name: str, start_date: date, end_date: date) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO season_passes (name, start_date, end_date, status)
                VALUES ($1, $2, $3, 'active')
                RETURNING id
                """,
                name,
                start_date,
                end_date,
            )

    async def get_season_progress(self, user_id: int, season_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM season_pass_progress
                WHERE user_id = $1 AND season_id = $2
                """,
                user_id,
                season_id,
            )
            return dict(row) if row else None

    async def upsert_season_progress(self, user_id: int, season_id: int, xp_delta: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO season_pass_progress (user_id, season_id, total_xp, tier)
                VALUES ($1, $2, $3, 0)
                ON CONFLICT (user_id, season_id) DO UPDATE SET
                    total_xp = season_pass_progress.total_xp + $3,
                    updated_at = NOW()
                RETURNING *
                """,
                user_id,
                season_id,
                xp_delta,
            )
            return dict(row) if row else {}

    async def update_season_tier(self, user_id: int, season_id: int, tier: int) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE season_pass_progress
                SET tier = $3, last_claimed_tier = $3, updated_at = NOW()
                WHERE user_id = $1 AND season_id = $2
                """,
                user_id,
                season_id,
                tier,
            )

    async def get_season_leaderboard(self, season_id: int, limit: int = 10) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sp.*, u.username
                FROM season_pass_progress sp
                JOIN users u ON u.user_id = sp.user_id
                WHERE sp.season_id = $1
                ORDER BY sp.total_xp DESC
                LIMIT $2
                """,
                season_id,
                limit,
            )
            return [dict(r) for r in rows]

    # --- 学習タイミング分析 ---

    async def get_study_timing_data(self, user_id: int, days: int = 30) -> dict:
        """時間帯別・曜日別の学習パターンを取得"""
        async with self.db_pool.acquire() as conn:
            cutoff = datetime.now(UTC) - timedelta(days=days)

            # 時間帯別の学習時間
            hourly = await conn.fetch(
                """
                SELECT EXTRACT(HOUR FROM logged_at) AS hour,
                       SUM(duration_minutes) AS total_minutes,
                       COUNT(*) AS session_count
                FROM study_logs
                WHERE user_id = $1 AND logged_at >= $2
                GROUP BY EXTRACT(HOUR FROM logged_at)
                ORDER BY hour
                """,
                user_id,
                cutoff,
            )

            # 曜日別の学習時間
            daily = await conn.fetch(
                """
                SELECT EXTRACT(DOW FROM logged_at) AS dow,
                       SUM(duration_minutes) AS total_minutes,
                       COUNT(*) AS session_count
                FROM study_logs
                WHERE user_id = $1 AND logged_at >= $2
                GROUP BY EXTRACT(DOW FROM logged_at)
                ORDER BY dow
                """,
                user_id,
                cutoff,
            )

            # ポモドーロの平均完了時間
            avg_pomo = await conn.fetchrow(
                """
                SELECT AVG(total_work_seconds) / 60.0 AS avg_work_minutes,
                       COUNT(*) AS total_completed
                FROM pomodoro_sessions
                WHERE user_id = $1 AND state = 'completed' AND created_at >= $2
                """,
                user_id,
                cutoff,
            )

        return {
            "hourly": [dict(r) for r in hourly],
            "daily": [dict(r) for r in daily],
            "avg_pomo_minutes": float(avg_pomo["avg_work_minutes"] or 0) if avg_pomo else 0,
            "total_completed_pomos": avg_pomo["total_completed"] if avg_pomo else 0,
        }

    # --- ウェルカムガイド ---

    async def ensure_user_level_with_flag(self, user_id: int) -> tuple[dict, bool]:
        """ユーザーレベル確保 + 新規ユーザーフラグ"""
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
            if row:
                # INSERT成功 = 新規ユーザー
                return dict(row), True
            # 既存ユーザー
            row = await conn.fetchrow(
                "SELECT * FROM user_levels WHERE user_id = $1",
                user_id,
            )
            return dict(row), False
