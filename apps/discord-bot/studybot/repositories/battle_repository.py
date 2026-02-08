"""チームバトル リポジトリ"""

import logging
from datetime import date

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class BattleRepository(BaseRepository):
    """team_battles / battle_contributions テーブル操作"""

    async def create_battle(
        self,
        guild_id: int,
        team_a_id: int,
        team_b_id: int,
        goal_type: str,
        duration_days: int,
        start_date: date,
        end_date: date,
        xp_multiplier: float = 2.0,
    ) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO team_battles
                    (guild_id, team_a_id, team_b_id, goal_type,
                     duration_days, start_date, end_date, xp_multiplier)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                guild_id, team_a_id, team_b_id, goal_type,
                duration_days, start_date, end_date, xp_multiplier,
            )
            return dict(row) if row else {}

    async def get_battle(self, battle_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM team_battles WHERE id = $1", battle_id
            )
            return dict(row) if row else None

    async def get_active_battles(self, guild_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tb.*,
                       ta.name AS team_a_name,
                       tb2.name AS team_b_name,
                       (SELECT COUNT(*) FROM team_members WHERE team_id = tb.team_a_id)
                           AS team_a_members,
                       (SELECT COUNT(*) FROM team_members WHERE team_id = tb.team_b_id)
                           AS team_b_members
                FROM team_battles tb
                JOIN study_teams ta ON ta.id = tb.team_a_id
                JOIN study_teams tb2 ON tb2.id = tb.team_b_id
                WHERE tb.guild_id = $1
                  AND tb.status IN ('pending', 'active')
                ORDER BY tb.created_at DESC
                """,
                guild_id,
            )
            return [dict(r) for r in rows]

    async def update_battle_status(
        self, battle_id: int, status: str
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE team_battles SET status = $2 WHERE id = $1",
                battle_id, status,
            )

    async def update_battle_score(
        self, battle_id: int, team_id: int, delta: int
    ) -> dict | None:
        async with self.db_pool.acquire() as conn:
            battle = await conn.fetchrow(
                "SELECT * FROM team_battles WHERE id = $1", battle_id
            )
            if not battle:
                return None

            if team_id == battle["team_a_id"]:
                col = "team_a_score"
            elif team_id == battle["team_b_id"]:
                col = "team_b_score"
            else:
                return None

            row = await conn.fetchrow(
                f"""
                UPDATE team_battles SET {col} = {col} + $2
                WHERE id = $1 RETURNING *
                """,
                battle_id, delta,
            )
            return dict(row) if row else None

    async def record_contribution(
        self,
        battle_id: int,
        user_id: int,
        team_id: int,
        amount: int,
        source: str = "discord",
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO battle_contributions
                    (battle_id, user_id, team_id, contribution, source)
                VALUES ($1, $2, $3, $4, $5)
                """,
                battle_id, user_id, team_id, amount, source,
            )

    async def get_battle_contributions(self, battle_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT bc.user_id, u.username, bc.team_id,
                       SUM(bc.contribution) AS total_contribution,
                       bc.source
                FROM battle_contributions bc
                JOIN users u ON u.user_id = bc.user_id
                WHERE bc.battle_id = $1
                GROUP BY bc.user_id, u.username, bc.team_id, bc.source
                ORDER BY total_contribution DESC
                """,
                battle_id,
            )
            return [dict(r) for r in rows]

    async def complete_battle(
        self, battle_id: int, winner_team_id: int | None
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE team_battles
                SET status = 'completed', winner_team_id = $2
                WHERE id = $1
                """,
                battle_id, winner_team_id,
            )

    async def get_user_active_battles(self, user_id: int) -> list[dict]:
        """ユーザーが参加中の全アクティブバトルを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tb.*, tm.team_id AS user_team_id
                FROM team_battles tb
                JOIN team_members tm ON (
                    tm.team_id = tb.team_a_id OR tm.team_id = tb.team_b_id
                )
                WHERE tm.user_id = $1
                  AND tb.status = 'active'
                """,
                user_id,
            )
            return [dict(r) for r in rows]

    async def get_expired_battles(self) -> list[dict]:
        """期限切れのアクティブバトルを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM team_battles
                WHERE status = 'active' AND end_date <= CURRENT_DATE
                """,
            )
            return [dict(r) for r in rows]
