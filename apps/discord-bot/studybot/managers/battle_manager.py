"""チームバトル マネージャー"""

import asyncio
import logging
from datetime import date, timedelta

from studybot.repositories.battle_repository import BattleRepository
from studybot.repositories.team_repository import TeamRepository

logger = logging.getLogger(__name__)


class BattleManager:
    """チームバトルのビジネスロジック"""

    def __init__(self, db_pool) -> None:
        self.db_pool = db_pool
        self.battle_repo = BattleRepository(db_pool)
        self.team_repo = TeamRepository(db_pool)
        self._lock = asyncio.Lock()

    async def create_battle(
        self,
        guild_id: int,
        team_a_id: int,
        team_b_id: int,
        goal_type: str = "study_minutes",
        duration_days: int = 7,
    ) -> dict:
        """バトル作成"""
        if team_a_id == team_b_id:
            return {"error": "同じチーム同士ではバトルできません"}

        if goal_type not in ("study_minutes", "pomodoro", "tasks"):
            return {"error": "無効なgoal_type: study_minutes/pomodoro/tasks"}

        if not 1 <= duration_days <= 30:
            return {"error": "期間は1-30日で指定してください"}

        team_a = await self.team_repo.get_team(team_a_id)
        team_b = await self.team_repo.get_team(team_b_id)
        if not team_a or not team_b:
            return {"error": "チームが見つかりません"}

        if team_a["guild_id"] != guild_id or team_b["guild_id"] != guild_id:
            return {"error": "同じサーバーのチームを指定してください"}

        start = date.today()
        end = start + timedelta(days=duration_days)

        battle = await self.battle_repo.create_battle(
            guild_id=guild_id,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            goal_type=goal_type,
            duration_days=duration_days,
            start_date=start,
            end_date=end,
        )

        return {
            "battle_id": battle["id"],
            "team_a_name": team_a["name"],
            "team_b_name": team_b["name"],
            "goal_type": goal_type,
            "duration_days": duration_days,
            "start_date": str(start),
            "end_date": str(end),
        }

    async def accept_battle(self, battle_id: int, user_id: int) -> dict:
        """バトル承認"""
        battle = await self.battle_repo.get_battle(battle_id)
        if not battle:
            return {"error": "バトルが見つかりません"}
        if battle["status"] != "pending":
            return {"error": "このバトルは既に開始/完了しています"}

        # Check if user is in team_b (opponent team)
        team_b = await self.team_repo.get_team(battle["team_b_id"])
        if not team_b:
            return {"error": "チームが見つかりません"}

        member = await self.team_repo.get_member(battle["team_b_id"], user_id)
        if not member:
            return {"error": "相手チームのメンバーのみ承認できます"}

        await self.battle_repo.update_battle_status(battle_id, "active")
        return {"status": "active", "battle_id": battle_id}

    async def add_contribution(
        self,
        user_id: int,
        goal_type: str,
        amount: int,
        source: str = "discord",
    ) -> None:
        """ユーザーの貢献を全アクティブバトルに記録"""
        battles = await self.battle_repo.get_user_active_battles(user_id)
        for battle in battles:
            if battle["goal_type"] != goal_type:
                continue

            team_id = battle["user_team_id"]
            async with self._lock:
                await self.battle_repo.record_contribution(
                    battle["id"], user_id, team_id, amount, source
                )
                await self.battle_repo.update_battle_score(
                    battle["id"], team_id, amount
                )

    async def check_battle_completion(self) -> list[dict]:
        """期限切れバトルをチェックして完了処理"""
        expired = await self.battle_repo.get_expired_battles()
        results = []
        for battle in expired:
            if battle["team_a_score"] > battle["team_b_score"]:
                winner = battle["team_a_id"]
            elif battle["team_b_score"] > battle["team_a_score"]:
                winner = battle["team_b_id"]
            else:
                winner = None  # draw

            await self.battle_repo.complete_battle(battle["id"], winner)
            results.append({
                "battle_id": battle["id"],
                "winner_team_id": winner,
                "team_a_score": battle["team_a_score"],
                "team_b_score": battle["team_b_score"],
            })
        return results

    async def get_battle_detail(self, battle_id: int) -> dict | None:
        """バトル詳細取得"""
        battle = await self.battle_repo.get_battle(battle_id)
        if not battle:
            return None

        team_a = await self.team_repo.get_team(battle["team_a_id"])
        team_b = await self.team_repo.get_team(battle["team_b_id"])
        contributions = await self.battle_repo.get_battle_contributions(battle_id)

        return {
            **battle,
            "team_a_name": team_a["name"] if team_a else "Unknown",
            "team_b_name": team_b["name"] if team_b else "Unknown",
            "team_a_members": team_a.get("member_count", 0) if team_a else 0,
            "team_b_members": team_b.get("member_count", 0) if team_b else 0,
            "contributions": contributions,
        }
