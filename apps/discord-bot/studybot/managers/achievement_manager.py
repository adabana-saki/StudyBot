"""実績システム ビジネスロジック"""

import logging

from studybot.repositories.achievement_repository import AchievementRepository

logger = logging.getLogger(__name__)


class AchievementManager:
    """実績システムの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = AchievementRepository(db_pool)

    async def check_and_update(
        self, user_id: int, achievement_key: str, new_value: int
    ) -> dict | None:
        """実績の進捗を更新し、アンロック条件をチェック"""
        # 実績を取得
        achievement = await self.repository.get_achievement_by_key(achievement_key)
        if not achievement:
            return None

        # 現在の進捗を取得
        current = await self.repository.get_user_progress(user_id, achievement_key)

        # 既にアンロック済みなら何もしない
        if current and current.get("unlocked"):
            return None

        # 進捗を更新
        progress = max(new_value, current["progress"] if current else 0)
        await self.repository.update_progress(user_id, achievement["id"], progress)

        # アンロック判定
        if progress >= achievement["target_value"]:
            await self.repository.unlock_achievement(user_id, achievement["id"])
            return {
                "unlocked": True,
                "achievement": achievement,
                "reward_coins": achievement["reward_coins"],
            }

        return None

    async def get_all_with_progress(self, user_id: int) -> list[dict]:
        """全実績とユーザーの進捗を取得"""
        return await self.repository.get_user_achievements(user_id)

    async def get_user_unlocked(self, user_id: int) -> list[dict]:
        """ユーザーがアンロック済みの実績を取得"""
        all_achievements = await self.repository.get_user_achievements(user_id)
        return [a for a in all_achievements if a.get("unlocked")]
