"""スタディチーム リポジトリ"""

import logging
import random
from datetime import date

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TeamRepository(BaseRepository):
    """study_teams / team_members テーブル操作"""

    async def create_team(
        self,
        name: str,
        creator_id: int,
        guild_id: int,
        max_members: int = 10,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO study_teams (name, creator_id, guild_id, max_members)
                VALUES ($1, $2, $3, $4)
                RETURNING id, name, creator_id, guild_id, max_members, created_at
                """,
                name,
                creator_id,
                guild_id,
                max_members,
            )
            return dict(row) if row else {}

    async def create_team_with_member(
        self,
        name: str,
        creator_id: int,
        guild_id: int,
        username: str,
        max_members: int = 10,
    ) -> dict:
        """チーム作成+作成者参加をトランザクションで実行"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO study_teams (name, creator_id, guild_id, max_members)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, name, creator_id, guild_id, max_members, created_at
                    """,
                    name,
                    creator_id,
                    guild_id,
                    max_members,
                )
                if not row:
                    return {}
                team = dict(row)
                await conn.execute(
                    """
                    INSERT INTO team_members (team_id, user_id, username)
                    VALUES ($1, $2, $3)
                    """,
                    team["id"],
                    creator_id,
                    username,
                )
                return team

    async def get_team(self, team_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT t.*,
                       (SELECT COUNT(*) FROM team_members WHERE team_id = t.id)
                           AS member_count
                FROM study_teams t
                WHERE t.id = $1
                """,
                team_id,
            )
            return dict(row) if row else None

    async def join_team(self, team_id: int, user_id: int, username: str) -> bool:
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO team_members (team_id, user_id, username)
                    VALUES ($1, $2, $3)
                    """,
                    team_id,
                    user_id,
                    username,
                )
                return True
            except Exception:
                logger.debug(
                    "チーム参加失敗 (team=%d, user=%d)",
                    team_id,
                    user_id,
                    exc_info=True,
                )
                return False

    async def leave_team(self, team_id: int, user_id: int) -> bool:
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM team_members WHERE team_id = $1 AND user_id = $2",
                team_id,
                user_id,
            )
            return result == "DELETE 1"

    async def get_team_members(self, team_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tm.user_id, tm.username, tm.joined_at
                FROM team_members tm
                WHERE tm.team_id = $1
                ORDER BY tm.joined_at
                """,
                team_id,
            )
            return [dict(r) for r in rows]

    async def get_member(self, team_id: int, user_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM team_members WHERE team_id = $1 AND user_id = $2",
                team_id,
                user_id,
            )
            return dict(row) if row else None

    async def get_user_teams(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*, tm.joined_at AS user_joined_at,
                       (SELECT COUNT(*) FROM team_members WHERE team_id = t.id)
                           AS member_count
                FROM study_teams t
                JOIN team_members tm ON tm.team_id = t.id
                WHERE tm.user_id = $1
                ORDER BY tm.joined_at DESC
                """,
                user_id,
            )
            return [dict(r) for r in rows]

    async def count_user_teams(self, user_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*) FROM study_teams
                WHERE creator_id = $1
                """,
                user_id,
            ) or 0

    async def get_team_stats(self, team_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(sl.duration_minutes), 0) AS total_minutes,
                    COUNT(DISTINCT sl.id) AS total_sessions,
                    COUNT(DISTINCT tm.user_id) AS member_count
                FROM team_members tm
                LEFT JOIN study_logs sl
                    ON sl.user_id = tm.user_id
                    AND sl.logged_at >= tm.joined_at
                WHERE tm.team_id = $1
                """,
                team_id,
            )
            if not row:
                return {
                    "total_minutes": 0,
                    "total_sessions": 0,
                    "member_count": 0,
                    "avg_minutes_per_member": 0,
                }
            member_count = row["member_count"] or 1
            total_minutes = row["total_minutes"] or 0
            return {
                "total_minutes": total_minutes,
                "total_sessions": row["total_sessions"] or 0,
                "member_count": member_count,
                "avg_minutes_per_member": round(total_minutes / member_count),
            }

    async def get_team_weekly_stats(self, team_id: int) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(sl.duration_minutes), 0) AS weekly_minutes,
                    COUNT(DISTINCT sl.id) AS weekly_sessions,
                    COUNT(DISTINCT tm.user_id) AS member_count
                FROM team_members tm
                LEFT JOIN study_logs sl
                    ON sl.user_id = tm.user_id
                    AND sl.logged_at >= NOW() - INTERVAL '7 days'
                WHERE tm.team_id = $1
                """,
                team_id,
            )
            if not row:
                return {
                    "weekly_minutes": 0,
                    "weekly_sessions": 0,
                    "member_count": 0,
                    "avg_weekly_minutes_per_member": 0,
                }
            member_count = row["member_count"] or 1
            weekly_minutes = row["weekly_minutes"] or 0
            return {
                "weekly_minutes": weekly_minutes,
                "weekly_sessions": row["weekly_sessions"] or 0,
                "member_count": member_count,
                "avg_weekly_minutes_per_member": round(
                    weekly_minutes / member_count
                ),
            }

    # --- チームクエスト ---

    async def get_team_quests(self, team_id: int, quest_date: date) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM team_quests
                WHERE team_id = $1 AND quest_date = $2
                ORDER BY id
                """,
                team_id,
                quest_date,
            )
            return [dict(r) for r in rows]

    async def create_team_quest(
        self,
        team_id: int,
        quest_type: str,
        target: int,
        reward_xp: int,
        reward_coins: int,
        quest_date: date,
    ) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO team_quests
                    (team_id, quest_type, target, reward_xp, reward_coins, quest_date)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                team_id,
                quest_type,
                target,
                reward_xp,
                reward_coins,
                quest_date,
            )

    async def update_team_quest_progress(
        self, team_id: int, quest_type: str, quest_date: date, delta: int
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE team_quests
                SET progress = LEAST(progress + $4, target),
                    completed = (progress + $4 >= target)
                WHERE team_id = $1
                  AND quest_type = $2
                  AND quest_date = $3
                  AND claimed = FALSE
                """,
                team_id,
                quest_type,
                quest_date,
                delta,
            )
            rows = await conn.fetch(
                """
                SELECT * FROM team_quests
                WHERE team_id = $1 AND quest_type = $2 AND quest_date = $3
                """,
                team_id,
                quest_type,
                quest_date,
            )
            return [dict(r) for r in rows]

    async def claim_team_quest(self, quest_id: int, team_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE team_quests
                SET claimed = TRUE
                WHERE id = $1 AND team_id = $2
                  AND completed = TRUE AND claimed = FALSE
                RETURNING *
                """,
                quest_id,
                team_id,
            )
            return dict(row) if row else None

    async def get_team_quest_by_id(self, quest_id: int, team_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM team_quests WHERE id = $1 AND team_id = $2",
                quest_id,
                team_id,
            )
            return dict(row) if row else None

    async def get_user_team_ids(self, user_id: int) -> list[int]:
        """ユーザーが参加している全チームIDを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT team_id FROM team_members WHERE user_id = $1",
                user_id,
            )
            return [r["team_id"] for r in rows]

    async def list_guild_teams(self, guild_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*,
                       (SELECT COUNT(*) FROM team_members WHERE team_id = t.id)
                           AS member_count
                FROM study_teams t
                WHERE t.guild_id = $1
                ORDER BY t.created_at DESC
                """,
                guild_id,
            )
            return [dict(r) for r in rows]
