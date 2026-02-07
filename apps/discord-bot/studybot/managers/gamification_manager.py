"""ゲーミフィケーション ビジネスロジック"""

import logging
from datetime import date, timedelta

from studybot.config.constants import LEVEL_FORMULA, XP_REWARDS
from studybot.repositories.gamification_repository import GamificationRepository

logger = logging.getLogger(__name__)


class GamificationManager:
    """XP/レベルシステムの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = GamificationRepository(db_pool)

    async def ensure_user(self, user_id: int, username: str = "") -> dict:
        """ユーザー初期化"""
        await self.repository.ensure_user(user_id, username)
        return await self.repository.ensure_user_level(user_id)

    async def add_xp(self, user_id: int, amount: int, reason: str) -> dict:
        """XPを付与してレベルアップチェック"""
        level_info = await self.repository.add_xp(user_id, amount, reason)
        if not level_info:
            return {"error": "XP付与に失敗しました"}

        old_level = level_info["level"]
        new_level = self._calculate_level(level_info["xp"])

        leveled_up = new_level > old_level
        milestone = None

        if leveled_up:
            await self.repository.update_level(user_id, new_level)
            milestone = await self.repository.get_milestone(new_level)

        return {
            "xp_gained": amount,
            "total_xp": level_info["xp"],
            "old_level": old_level,
            "new_level": new_level,
            "leveled_up": leveled_up,
            "milestone": milestone,
            "next_level_xp": LEVEL_FORMULA(new_level + 1),
        }

    def _calculate_level(self, total_xp: int) -> int:
        """累計XPからレベルを計算"""
        level = 1
        accumulated = 0
        while True:
            needed = LEVEL_FORMULA(level + 1)
            if accumulated + needed > total_xp:
                break
            accumulated += needed
            level += 1
        return level

    async def check_streak(self, user_id: int) -> dict:
        """連続学習日数をチェック・更新"""
        level_info = await self.repository.get_user_level(user_id)
        if not level_info:
            return {"streak": 0, "bonus": False}

        today = date.today()
        last_study = level_info.get("last_study_date")

        if last_study == today:
            return {"streak": level_info["streak_days"], "bonus": False}

        if last_study == today - timedelta(days=1):
            new_streak = level_info["streak_days"] + 1
        else:
            new_streak = 1

        await self.repository.update_streak(user_id, new_streak, today)

        # 7日連続でボーナスXP
        bonus = new_streak > 0 and new_streak % 7 == 0
        if bonus:
            await self.repository.add_xp(user_id, XP_REWARDS["streak_bonus"], "連続学習ボーナス")

        return {"streak": new_streak, "bonus": bonus}

    async def get_profile(self, user_id: int) -> dict | None:
        """ユーザープロフィールを取得"""
        level_info = await self.repository.get_user_level(user_id)
        if not level_info:
            return None

        current_level = level_info["level"]
        rank = await self.repository.get_user_rank(user_id)
        milestone = await self.repository.get_milestone(current_level)

        # 次のレベルまでの進捗
        next_xp = LEVEL_FORMULA(current_level + 1)
        # 現在のレベルまでに消費したXP
        consumed = sum(LEVEL_FORMULA(lv + 1) for lv in range(1, current_level))
        current_progress = level_info["xp"] - consumed

        return {
            "user_id": user_id,
            "xp": level_info["xp"],
            "level": current_level,
            "streak_days": level_info["streak_days"],
            "rank": rank,
            "badge": milestone["badge"] if milestone else "🌱",
            "next_level_xp": next_xp,
            "current_progress": max(0, current_progress),
        }
