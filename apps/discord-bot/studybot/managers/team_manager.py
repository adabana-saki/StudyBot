"""スタディチーム ビジネスロジック"""

import logging
import random
from datetime import date, timedelta, timezone

from studybot.repositories.team_repository import TeamRepository

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

# チーム制限
MAX_TEAMS_PER_USER = 3
MIN_TEAM_NAME_LENGTH = 2
MAX_TEAM_NAME_LENGTH = 50

# チームクエスト定義
TEAM_QUEST_TEMPLATES = [
    {
        "quest_type": "team_study_minutes",
        "label": "チーム合計学習時間",
        "targets": [60, 120, 180, 300],
        "xp_per_unit": 0.3,
        "coins_per_unit": 0.2,
        "unit": "分",
    },
    {
        "quest_type": "team_pomodoro",
        "label": "チーム合計ポモドーロ",
        "targets": [3, 5, 8, 12],
        "xp_per_unit": 10,
        "coins_per_unit": 8,
        "unit": "回",
    },
    {
        "quest_type": "team_tasks",
        "label": "チーム合計タスク完了",
        "targets": [5, 10, 15, 20],
        "xp_per_unit": 8,
        "coins_per_unit": 5,
        "unit": "件",
    },
]


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

    # --- チームクエスト ---

    def _today_jst(self) -> date:
        from datetime import datetime
        return datetime.now(JST).date()

    async def get_team_quests(self, team_id: int) -> list[dict]:
        """チームの本日クエストを取得（なければ生成）"""
        today = self._today_jst()
        quests = await self.repository.get_team_quests(team_id, today)
        if not quests:
            quests = await self._generate_team_quests(team_id, today)
        return quests

    async def _generate_team_quests(self, team_id: int, quest_date: date) -> list[dict]:
        """チームクエストを生成"""
        templates = random.sample(
            TEAM_QUEST_TEMPLATES, min(2, len(TEAM_QUEST_TEMPLATES))
        )
        quests = []
        for tmpl in templates:
            target = random.choice(tmpl["targets"])
            reward_xp = max(15, int(target * tmpl["xp_per_unit"]))
            reward_coins = max(10, int(target * tmpl["coins_per_unit"]))
            quest_id = await self.repository.create_team_quest(
                team_id=team_id,
                quest_type=tmpl["quest_type"],
                target=target,
                reward_xp=reward_xp,
                reward_coins=reward_coins,
                quest_date=quest_date,
            )
            quests.append({
                "id": quest_id,
                "team_id": team_id,
                "quest_type": tmpl["quest_type"],
                "target": target,
                "progress": 0,
                "reward_xp": reward_xp,
                "reward_coins": reward_coins,
                "completed": False,
                "claimed": False,
                "quest_date": quest_date,
            })
        return quests

    async def update_team_quest_progress(
        self, user_id: int, quest_type: str, delta: int = 1
    ) -> None:
        """ユーザーの全チームのクエスト進捗を更新"""
        today = self._today_jst()
        team_ids = await self.repository.get_user_team_ids(user_id)
        for team_id in team_ids:
            try:
                await self.repository.update_team_quest_progress(
                    team_id, quest_type, today, delta
                )
            except Exception:
                logger.debug("チームクエスト進捗更新失敗 team=%d", team_id, exc_info=True)

    async def claim_team_quest(self, team_id: int, quest_id: int) -> dict:
        """チームクエスト報酬を受け取る"""
        quest = await self.repository.get_team_quest_by_id(quest_id, team_id)
        if not quest:
            return {"error": "クエストが見つかりません"}
        if quest["claimed"]:
            return {"error": "既に報酬を受け取り済みです"}
        if not quest["completed"]:
            return {"error": "クエストがまだ完了していません"}

        result = await self.repository.claim_team_quest(quest_id, team_id)
        if not result:
            return {"error": "報酬の受け取りに失敗しました"}

        return {
            "quest_id": result["id"],
            "quest_type": result["quest_type"],
            "reward_xp": result["reward_xp"],
            "reward_coins": result["reward_coins"],
        }

    def get_team_quest_label(self, quest_type: str) -> str:
        for tmpl in TEAM_QUEST_TEMPLATES:
            if tmpl["quest_type"] == quest_type:
                return tmpl["label"]
        return quest_type

    def get_team_quest_unit(self, quest_type: str) -> str:
        for tmpl in TEAM_QUEST_TEMPLATES:
            if tmpl["quest_type"] == quest_type:
                return tmpl["unit"]
        return ""
