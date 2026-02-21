"""フォージ（熟練の鍛冶場）DB操作"""

import logging

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ForgeRepository(BaseRepository):
    """フォージのCRUD"""

    # --- スキル ---

    async def get_skill(self, user_id: int, category: str) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM forge_skills
                WHERE user_id = $1 AND category = $2
                """,
                user_id,
                category,
            )
        return dict(row) if row else {}

    async def get_all_skills(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM forge_skills
                WHERE user_id = $1
                ORDER BY mastery_xp DESC
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def upsert_skill(
        self,
        user_id: int,
        category: str,
        mastery_xp: int,
        mastery_level: int,
        quality_avg: float,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO forge_skills
                    (user_id, category, mastery_xp, mastery_level, quality_avg)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, category)
                DO UPDATE SET mastery_xp = $3, mastery_level = $4,
                             quality_avg = $5, updated_at = NOW()
                RETURNING *
                """,
                user_id,
                category,
                mastery_xp,
                mastery_level,
                quality_avg,
            )
        return dict(row) if row else {}

    async def add_mastery_xp(self, user_id: int, category: str, xp_delta: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO forge_skills (user_id, category, mastery_xp)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, category)
                DO UPDATE SET mastery_xp = forge_skills.mastery_xp + $3,
                             updated_at = NOW()
                RETURNING *
                """,
                user_id,
                category,
                xp_delta,
            )
        return dict(row) if row else {}

    # --- 品質ログ ---

    async def log_quality(
        self,
        user_id: int,
        category: str,
        focus: int,
        difficulty: int,
        progress: int,
        quality_score: float,
        duration_minutes: int,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO forge_quality_logs
                    (user_id, category, focus, difficulty, progress,
                     quality_score, duration_minutes)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                user_id,
                category,
                focus,
                difficulty,
                progress,
                quality_score,
                duration_minutes,
            )
        return dict(row) if row else {}

    async def get_quality_logs(
        self, user_id: int, category: str = "", limit: int = 10
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            if category:
                rows = await conn.fetch(
                    """
                    SELECT * FROM forge_quality_logs
                    WHERE user_id = $1 AND category = $2
                    ORDER BY logged_at DESC LIMIT $3
                    """,
                    user_id,
                    category,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM forge_quality_logs
                    WHERE user_id = $1
                    ORDER BY logged_at DESC LIMIT $2
                    """,
                    user_id,
                    limit,
                )
        return [dict(r) for r in rows]

    async def get_quality_average(self, user_id: int, category: str = "") -> float:
        async with self.db_pool.acquire() as conn:
            if category:
                val = await conn.fetchval(
                    """
                    SELECT COALESCE(AVG(quality_score), 0)
                    FROM forge_quality_logs
                    WHERE user_id = $1 AND category = $2
                    """,
                    user_id,
                    category,
                )
            else:
                val = await conn.fetchval(
                    """
                    SELECT COALESCE(AVG(quality_score), 0)
                    FROM forge_quality_logs
                    WHERE user_id = $1
                    """,
                    user_id,
                )
        return float(val)

    async def get_quality_trend(self, user_id: int, days: int = 7) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT logged_at::date as day,
                       AVG(quality_score) as avg_quality,
                       COUNT(*) as sessions
                FROM forge_quality_logs
                WHERE user_id = $1
                  AND logged_at > NOW() - INTERVAL '1 day' * $2
                GROUP BY logged_at::date
                ORDER BY day
                """,
                user_id,
                days,
            )
        return [dict(r) for r in rows]

    # --- Eloレーティング ---

    async def get_rating(self, user_id: int, category: str) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM forge_ratings
                WHERE user_id = $1 AND category = $2
                """,
                user_id,
                category,
            )
        return dict(row) if row else {}

    async def upsert_rating(
        self,
        user_id: int,
        category: str,
        rating: int,
        wins: int,
        losses: int,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO forge_ratings (user_id, category, rating, wins, losses)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, category)
                DO UPDATE SET rating = $3, wins = $4, losses = $5,
                             updated_at = NOW()
                RETURNING *
                """,
                user_id,
                category,
                rating,
                wins,
                losses,
            )
        return dict(row) if row else {}

    async def get_leaderboard(self, category: str, limit: int = 10) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.*, u.username
                FROM forge_ratings r
                JOIN users u ON u.user_id = r.user_id
                WHERE r.category = $1
                ORDER BY r.rating DESC
                LIMIT $2
                """,
                category,
                limit,
            )
        return [dict(r) for r in rows]

    # --- チャレンジ ---

    async def create_challenge(
        self,
        creator_id: int,
        title: str,
        description: str,
        category: str,
        difficulty_rating: int = 1200,
        is_template: bool = False,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO forge_challenges
                    (creator_id, title, description, category,
                     difficulty_rating, is_template)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                creator_id,
                title,
                description,
                category,
                difficulty_rating,
                is_template,
            )
        return dict(row) if row else {}

    async def get_challenge(self, challenge_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM forge_challenges WHERE id = $1",
                challenge_id,
            )
        return dict(row) if row else {}

    async def list_challenges(
        self, category: str = "", limit: int = 20, offset: int = 0
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            if category:
                rows = await conn.fetch(
                    """
                    SELECT * FROM forge_challenges
                    WHERE active = TRUE AND category = $1
                    ORDER BY difficulty_rating
                    LIMIT $2 OFFSET $3
                    """,
                    category,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM forge_challenges
                    WHERE active = TRUE
                    ORDER BY difficulty_rating
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
        return [dict(r) for r in rows]

    async def update_challenge_stats(
        self,
        challenge_id: int,
        new_rating: int,
        inc_attempts: bool = True,
        inc_success: bool = False,
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE forge_challenges
                SET difficulty_rating = $2,
                    attempt_count = attempt_count + $3,
                    success_count = success_count + $4
                WHERE id = $1
                """,
                challenge_id,
                new_rating,
                1 if inc_attempts else 0,
                1 if inc_success else 0,
            )

    async def create_challenge_attempt(
        self,
        challenge_id: int,
        user_id: int,
        passed: bool,
        user_rating_before: int,
        user_rating_after: int,
        challenge_rating_before: int,
        challenge_rating_after: int,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO forge_challenge_attempts
                    (challenge_id, user_id, passed,
                     user_rating_before, user_rating_after,
                     challenge_rating_before, challenge_rating_after)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                challenge_id,
                user_id,
                passed,
                user_rating_before,
                user_rating_after,
                challenge_rating_before,
                challenge_rating_after,
            )
        return dict(row) if row else {}

    # --- ピアレビュー ---

    async def create_submission(
        self, user_id: int, category: str, title: str, description: str
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO forge_submissions
                    (user_id, category, title, description)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                user_id,
                category,
                title,
                description,
            )
        return dict(row) if row else {}

    async def get_submission(self, submission_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM forge_submissions WHERE id = $1",
                submission_id,
            )
        return dict(row) if row else {}

    async def get_open_submissions(
        self, category: str = "", exclude_user_id: int = 0, limit: int = 10
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            if category:
                rows = await conn.fetch(
                    """
                    SELECT * FROM forge_submissions
                    WHERE status = 'open' AND user_id != $1 AND category = $2
                    ORDER BY created_at DESC LIMIT $3
                    """,
                    exclude_user_id,
                    category,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM forge_submissions
                    WHERE status = 'open' AND user_id != $1
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    exclude_user_id,
                    limit,
                )
        return [dict(r) for r in rows]

    async def claim_submission(self, submission_id: int, reviewer_id: int) -> bool:
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE forge_submissions
                SET status = 'claimed'
                WHERE id = $1 AND status = 'open'
                """,
                submission_id,
            )
        return result == "UPDATE 1"

    async def create_review(
        self,
        submission_id: int,
        reviewer_id: int,
        quality_rating: int,
        feedback: str,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO forge_reviews
                    (submission_id, reviewer_id, quality_rating, feedback)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                submission_id,
                reviewer_id,
                quality_rating,
                feedback,
            )
            await conn.execute(
                """
                UPDATE forge_submissions SET status = 'reviewed'
                WHERE id = $1
                """,
                submission_id,
            )
        return dict(row) if row else {}
