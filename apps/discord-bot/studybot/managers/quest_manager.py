"""デイリークエスト ビジネスロジック"""

import logging
import random
from datetime import date, datetime, timedelta, timezone

from studybot.repositories.quest_repository import QuestRepository

logger = logging.getLogger(__name__)

# 日本標準時 (UTC+9)
JST = timezone(timedelta(hours=9))

# クエスト定義
QUEST_TEMPLATES = [
    {
        "quest_type": "complete_pomodoro",
        "label": "ポモドーロ完了",
        "targets": [1, 2, 3, 5],
        "xp_per_unit": 15,
        "coins_per_unit": 10,
        "activity_key": "pomodoro_count",
    },
    {
        "quest_type": "study_minutes",
        "label": "学習時間",
        "targets": [30, 60, 90, 120],
        "xp_per_unit": 0.5,
        "coins_per_unit": 0.3,
        "activity_key": "study_minutes",
    },
    {
        "quest_type": "complete_tasks",
        "label": "タスク完了",
        "targets": [1, 2, 3, 5],
        "xp_per_unit": 15,
        "coins_per_unit": 10,
        "activity_key": "tasks_completed",
    },
    {
        "quest_type": "log_study",
        "label": "学習ログ記録",
        "targets": [1, 2, 3],
        "xp_per_unit": 20,
        "coins_per_unit": 12,
        "activity_key": "log_count",
    },
]

# ボーナスクエスト（チェイン報酬）
CHAIN_BONUS_TEMPLATE = {
    "quest_type": "study_minutes",
    "label": "チェインボーナス",
    "xp_multiplier": 2.0,
    "coins_multiplier": 2.0,
}

# チェインボーナスのマイルストーン
CHAIN_MILESTONES = [3, 5, 7, 14, 30]


def _today_jst() -> date:
    """JSTでの今日の日付を返す"""
    return datetime.now(JST).date()


def _generate_smart_quests(
    user_id: int, quest_date: date, activity: dict | None = None
) -> list[dict]:
    """アクティビティに基づいてスマートクエストを生成"""
    if not activity:
        # データなし = ランダムフォールバック
        return _generate_random_quests(user_id, quest_date)

    # アクティビティの重み計算: よく使う機能に高い確率を割り当て
    weights = []
    for tmpl in QUEST_TEMPLATES:
        key = tmpl.get("activity_key", "")
        count = activity.get(key, 0) or 0
        # 最低重み1 + アクティビティに応じたボーナス
        weight = 1 + min(count, 20)
        weights.append(weight)

    # 重み付きサンプリングで3つ選択（重複なし）
    selected = []
    remaining = list(range(len(QUEST_TEMPLATES)))
    remaining_weights = list(weights)

    for _ in range(min(3, len(QUEST_TEMPLATES))):
        if not remaining:
            break
        chosen = random.choices(remaining, weights=remaining_weights, k=1)[0]
        idx = remaining.index(chosen)
        selected.append(QUEST_TEMPLATES[chosen])
        remaining.pop(idx)
        remaining_weights.pop(idx)

    quests = []
    for tmpl in selected:
        # アクティビティレベルに基づいてターゲットを調整
        key = tmpl.get("activity_key", "")
        user_activity = activity.get(key, 0) or 0

        if user_activity == 0:
            # 未使用機能は最低ターゲット
            target = tmpl["targets"][0]
        elif user_activity < 5:
            # 低アクティビティ: 低〜中ターゲット
            target = random.choice(tmpl["targets"][: len(tmpl["targets"]) // 2 + 1])
        else:
            # 高アクティビティ: 全範囲から選択
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


def _generate_random_quests(user_id: int, quest_date: date) -> list[dict]:
    """ランダムクエスト生成（フォールバック）"""
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
        """今日のデイリークエストを取得（なければスマート生成）"""
        await self.repository.ensure_user(user_id, username)

        today = _today_jst()
        quests = await self.repository.get_user_quests(user_id, today)

        if not quests:
            # スマートクエスト: ユーザーアクティビティプロファイルを分析
            try:
                activity = await self.repository.get_user_activity_profile(user_id)
            except Exception:
                logger.debug("アクティビティプロファイル取得失敗", exc_info=True)
                activity = None

            generated = _generate_smart_quests(user_id, today, activity)

            # チェインボーナスチェック
            try:
                chain_days = await self.repository.get_consecutive_quest_days(user_id)
                if chain_days > 0 and chain_days in CHAIN_MILESTONES:
                    bonus = _generate_chain_bonus_quest(user_id, today, chain_days)
                    if bonus:
                        generated.append(bonus)
            except Exception:
                logger.debug("チェインボーナスチェック失敗", exc_info=True)

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

    async def get_chain_streak(self, user_id: int) -> int:
        """クエストチェインの連続日数を取得"""
        return await self.repository.get_consecutive_quest_days(user_id)

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


def _generate_chain_bonus_quest(
    user_id: int, quest_date: date, chain_days: int
) -> dict | None:
    """チェインボーナスクエストを生成"""
    base_target = 30 + chain_days * 5  # チェインが長いほど高い目標
    base_xp = max(30, int(base_target * 0.5 * CHAIN_BONUS_TEMPLATE["xp_multiplier"]))
    base_coins = max(20, int(base_target * 0.3 * CHAIN_BONUS_TEMPLATE["coins_multiplier"]))

    return {
        "user_id": user_id,
        "quest_type": CHAIN_BONUS_TEMPLATE["quest_type"],
        "target": base_target,
        "reward_xp": base_xp,
        "reward_coins": base_coins,
        "quest_date": quest_date,
    }
