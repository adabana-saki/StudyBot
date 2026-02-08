"""スタディチーム ビジネスロジック"""

import logging

from studybot.repositories.team_repository import TeamRepository

logger = logging.getLogger(__name__)

# チーム制限
MAX_TEAMS_PER_USER = 3
MIN_TEAM_NAME_LENGTH = 2
MAX_TEAM_NAME_LENGTH = 50


class TeamManager:
    """スタディチームの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = TeamRepository(db_pool)

    async def create_team(
        self,
        creator_id: int,
        username: str,
        guild_id: int,
        name: str,
        max_members: int = 10,
    ) -> dict:
        await self.repository.ensure_user(creator_id, username)

        # チーム名バリデーション
        name = name.strip()
        if len(name) < MIN_TEAM_NAME_LENGTH:
            return {"error": f"チーム名は{MIN_TEAM_NAME_LENGTH}文字以上にしてください"}
        if len(name) > MAX_TEAM_NAME_LENGTH:
            return {"error": f"チーム名は{MAX_TEAM_NAME_LENGTH}文字以内にしてください"}

        # 作成数上限チェック
        team_count = await self.repository.count_user_teams(creator_id)
        if team_count >= MAX_TEAMS_PER_USER:
            return {"error": f"チームは最大{MAX_TEAMS_PER_USER}つまで作成できます"}

        team = await self.repository.create_team_with_member(
            name=name,
            creator_id=creator_id,
            guild_id=guild_id,
            username=username,
            max_members=max_members,
        )

        if not team:
            return {"error": "チーム作成に失敗しました"}

        return {
            "team_id": team["id"],
            "name": team["name"],
            "max_members": team["max_members"],
        }

    async def join_team(
        self, team_id: int, user_id: int, username: str
    ) -> dict:
        await self.repository.ensure_user(user_id, username)

        team = await self.repository.get_team(team_id)
        if not team:
            return {"error": "チームが見つかりません"}

        # 既にメンバーかチェック
        existing = await self.repository.get_member(team_id, user_id)
        if existing:
            return {"error": "既にこのチームに参加しています"}

        # 満員チェック
        if team["member_count"] >= team["max_members"]:
            return {"error": "このチームは満員です"}

        success = await self.repository.join_team(team_id, user_id, username)
        if not success:
            return {"error": "参加に失敗しました"}

        return {
            "team_id": team_id,
            "name": team["name"],
            "member_count": team["member_count"] + 1,
        }

    async def leave_team(self, team_id: int, user_id: int) -> dict:
        team = await self.repository.get_team(team_id)
        if not team:
            return {"error": "チームが見つかりません"}

        existing = await self.repository.get_member(team_id, user_id)
        if not existing:
            return {"error": "このチームに参加していません"}

        success = await self.repository.leave_team(team_id, user_id)
        if not success:
            return {"error": "脱退に失敗しました"}

        return {
            "team_id": team_id,
            "name": team["name"],
        }

    async def get_team_stats(self, team_id: int) -> dict | None:
        team = await self.repository.get_team(team_id)
        if not team:
            return None

        stats = await self.repository.get_team_stats(team_id)
        weekly = await self.repository.get_team_weekly_stats(team_id)

        return {
            "team": team,
            "stats": stats,
            "weekly": weekly,
        }

    async def get_team_members(self, team_id: int) -> dict:
        team = await self.repository.get_team(team_id)
        if not team:
            return {"error": "チームが見つかりません"}

        members = await self.repository.get_team_members(team_id)
        return {
            "team": team,
            "members": members,
        }

    async def list_guild_teams(self, guild_id: int) -> list[dict]:
        return await self.repository.list_guild_teams(guild_id)

    async def get_user_teams(self, user_id: int) -> list[dict]:
        return await self.repository.get_user_teams(user_id)
