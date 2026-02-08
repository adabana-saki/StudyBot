"""デイリークエスト ビジネスロジック"""

import logging
import random
from datetime import date, datetime, timezone, timedelta

from studybot.repositories.quest_repository import QuestRepository

logger = logging.getLogger(__name__)

# 日本標準時 (UTC+9)
JST = timezone(timedelta(hours=9))

# クエスト定義: (quest_type, label, (min_target, max_target), xp_base, coins_base)
QUEST_TEMPLATES = [
    {
        "quest_type": "complete_pomodoro",
        "label": "ポモドーロ完了",
        "targets": [1, 2, 3, 5],
        "xp_per_unit": 15,
        "coins_per_unit": 10,
    },
    {
        "quest_type": "study_minutes",
        "label": "学習時間",
        "targets": [30, 60, 90, 120],
        "xp_per_unit": 0.5,
        "coins_per_unit": 0.3,
    },
    {
        "quest_type": "complete_tasks",
        "label": "タスク完了",
        "targets": [1, 2, 3, 5],
        "xp_per_unit": 15,
        "coins_per_unit": 10,
    },
    {
        "quest_type": "log_study",
        "label": "学習ログ記録",
        "targets": [1, 2, 3],
        "xp_per_unit": 20,
        "coins_per_unit": 12,
    },
]


def _today_jst() -> date:
    """JSTでの今日の日付を返す"""
    return datetime.now(JST).date()


def _generate_quests(user_id: int, quest_date: date) -> list[dict]:
    """3つのランダムクエストを生成"""
    templates = random.sample(QUEST_TEMPLATES, min(3, len(QUEST_TEMPLATES)))
    quests = []
    for tmpl in templates:
        target = random.choice(tmpl["targets"])
        reward_xp = max(10, int(target * tmpl["xp_per_unit"]))
        reward_coins = max(5, int(target * tmpl["coins_per_unit"]))
        quests.append(
            {
                "user_id": user_id,
                "quest_type": tmpl["quest_type"],
                "target": target,
                "reward_xp": reward_xp,
                "reward_coins": reward_coins,
                "quest_date": quest_date,
            }
        )
    return quests


class QuestManager:
    """デイリークエストの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = QuestRepository(db_pool)

    async def get_daily_quests(self, user_id: int, username: str) -> list[dict]:
        """今日のデイリークエストを取得（なければ自動生成）"""
        await self.repository.ensure_user(user_id, username)

        today = _today_jst()
        quests = await self.repository.get_user_quests(user_id, today)

        if not quests:
            # 今日のクエストがまだない場合は生成
            generated = _generate_quests(user_id, today)
            for q in generated:
                quest_id = await self.repository.create_quest(
                    user_id=q["user_id"],
                    quest_type=q["quest_type"],
                    target=q["target"],
                    reward_xp=q["reward_xp"],
                    reward_coins=q["reward_coins"],
                    quest_date=q["quest_date"],
                )
                q["id"] = quest_id
                q["progress"] = 0
                q["completed"] = False
                q["claimed"] = False
            quests = generated

        return quests

    async def update_progress(
        self, user_id: int, quest_type: str, delta: int = 1
    ) -> list[dict]:
        """クエスト進捗を更新"""
        today = _today_jst()
        return await self.repository.update_progress(user_id, quest_type, today, delta)

    async def claim_quest(self, user_id: int, quest_id: int) -> dict:
        """クエスト報酬を受け取る"""
        quest = await self.repository.get_quest_by_id(quest_id, user_id)
        if not quest:
            return {"error": "クエストが見つかりません"}

        if quest["claimed"]:
            return {"error": "既に報酬を受け取り済みです"}

        if not quest["completed"]:
            return {"error": "クエストがまだ完了していません"}

        result = await self.repository.claim_quest(quest_id, user_id)
        if not result:
            return {"error": "報酬の受け取りに失敗しました"}

        return {
            "quest_id": result["id"],
            "quest_type": result["quest_type"],
            "reward_xp": result["reward_xp"],
            "reward_coins": result["reward_coins"],
        }

    def get_quest_label(self, quest_type: str) -> str:
        """クエストタイプの日本語ラベルを取得"""
        for tmpl in QUEST_TEMPLATES:
            if tmpl["quest_type"] == quest_type:
                return tmpl["label"]
        return quest_type

    def get_quest_unit(self, quest_type: str) -> str:
        """クエストタイプの単位を取得"""
        units = {
            "complete_pomodoro": "回",
            "study_minutes": "分",
            "complete_tasks": "件",
            "log_study": "回",
        }
        return units.get(quest_type, "")
