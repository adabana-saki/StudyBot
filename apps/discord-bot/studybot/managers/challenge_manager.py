"""チャレンジ ビジネスロジック"""

import logging
from datetime import date, timedelta

from studybot.repositories.challenge_repository import ChallengeRepository

logger = logging.getLogger(__name__)


class ChallengeManager:
    """コホートチャレンジの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = ChallengeRepository(db_pool)

    async def create_challenge(
        self,
        creator_id: int,
        username: str,
        guild_id: int,
        name: str,
        duration_days: int,
        goal_type: str = "study_minutes",
        goal_target: int = 0,
        description: str = "",
        xp_multiplier: float = 1.5,
    ) -> dict:
        await self.repository.ensure_user(creator_id, username)

        if duration_days < 3 or duration_days > 90:
            return {"error": "期間は3〜90日の間で設定してください"}

        start_date = date.today()
        end_date = start_date + timedelta(days=duration_days)

        challenge_id = await self.repository.create_challenge(
            creator_id=creator_id,
            guild_id=guild_id,
            name=name,
            description=description,
            goal_type=goal_type,
            goal_target=goal_target,
            duration_days=duration_days,
            start_date=start_date,
            end_date=end_date,
            xp_multiplier=xp_multiplier,
        )

        # 作成者を自動参加
        await self.repository.join_challenge(challenge_id, creator_id)
        # ステータスをactiveに
        await self.repository.update_status(challenge_id, "active")

        return {
            "challenge_id": challenge_id,
            "name": name,
            "duration_days": duration_days,
            "goal_type": goal_type,
            "goal_target": goal_target,
            "start_date": str(start_date),
            "end_date": str(end_date),
        }

    async def join_challenge(self, challenge_id: int, user_id: int, username: str) -> dict:
        await self.repository.ensure_user(user_id, username)
        challenge = await self.repository.get_challenge(challenge_id)
        if not challenge:
            return {"error": "チャレンジが見つかりません"}
        if challenge["status"] != "active":
            return {"error": "このチャレンジは参加受付していません"}

        existing = await self.repository.get_participant(challenge_id, user_id)
        if existing:
            return {"error": "既に参加しています"}

        success = await self.repository.join_challenge(challenge_id, user_id)
        if not success:
            return {"error": "参加に失敗しました"}

        return {
            "challenge_id": challenge_id,
            "name": challenge["name"],
            "participant_count": challenge["participant_count"] + 1,
        }

    async def checkin(
        self,
        challenge_id: int,
        user_id: int,
        progress_delta: int,
        note: str = "",
    ) -> dict:
        challenge = await self.repository.get_challenge(challenge_id)
        if not challenge:
            return {"error": "チャレンジが見つかりません"}
        if challenge["status"] != "active":
            return {"error": "このチャレンジはアクティブではありません"}

        participant = await self.repository.get_participant(challenge_id, user_id)
        if not participant:
            return {"error": "このチャレンジに参加していません"}

        result = await self.repository.checkin(challenge_id, user_id, progress_delta, note)
        return {
            "progress": result.get("progress", 0),
            "goal_target": challenge["goal_target"],
            "completed": result.get("completed", False),
            "checkins": result.get("checkins", 0),
            "challenge_name": challenge["name"],
        }

    async def get_challenge(self, challenge_id: int) -> dict | None:
        return await self.repository.get_challenge(challenge_id)

    async def list_challenges(self, guild_id: int, status: str | None = None) -> list[dict]:
        return await self.repository.list_challenges(guild_id, status)

    async def get_leaderboard(self, challenge_id: int) -> list[dict]:
        return await self.repository.get_leaderboard(challenge_id)

    async def check_expired_challenges(self, guild_id: int) -> int:
        """期限切れチャレンジを完了にする"""
        challenges = await self.repository.list_challenges(guild_id, "active")
        count = 0
        today = date.today()
        for c in challenges:
            if c["end_date"] <= today:
                await self.repository.update_status(c["id"], "completed")
                count += 1
        return count
