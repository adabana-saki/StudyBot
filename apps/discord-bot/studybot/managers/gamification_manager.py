"""ゲーミフィケーション ビジネスロジック"""

import logging
from datetime import date, timedelta

from studybot.config.constants import LEVEL_FORMULA, XP_REWARDS
from studybot.repositories.gamification_repository import GamificationRepository

logger = logging.getLogger(__name__)

FOCUS_SCORE_GRADES = [
    (90, "S"),
    (75, "A"),
    (60, "B"),
    (40, "C"),
    (0, "D"),
]

# シーズンパス tier 定義
SEASON_TIERS = [
    {"tier": 1, "xp_required": 100, "reward_coins": 50, "label": "ブロンズ I"},
    {"tier": 2, "xp_required": 300, "reward_coins": 75, "label": "ブロンズ II"},
    {"tier": 3, "xp_required": 600, "reward_coins": 100, "label": "ブロンズ III"},
    {"tier": 4, "xp_required": 1000, "reward_coins": 150, "label": "シルバー I"},
    {"tier": 5, "xp_required": 1500, "reward_coins": 200, "label": "シルバー II"},
    {"tier": 6, "xp_required": 2000, "reward_coins": 250, "label": "シルバー III"},
    {"tier": 7, "xp_required": 3000, "reward_coins": 350, "label": "ゴールド I"},
    {"tier": 8, "xp_required": 4000, "reward_coins": 500, "label": "ゴールド II"},
    {"tier": 9, "xp_required": 5500, "reward_coins": 750, "label": "ゴールド III"},
    {"tier": 10, "xp_required": 7500, "reward_coins": 1000, "label": "ダイヤモンド"},
]


class GamificationManager:
    """XP/レベルシステムの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = GamificationRepository(db_pool)

    async def ensure_user(self, user_id: int, username: str = "") -> tuple[dict, bool]:
        """ユーザー初期化。(level_data, is_new_user) を返す"""
        await self.repository.ensure_user(user_id, username)
        return await self.repository.ensure_user_level_with_flag(user_id)

    async def add_xp(self, user_id: int, amount: int, reason: str) -> dict:
        """XPを付与してレベルアップチェック（チャレンジ乗算器適用）"""
        # アクティブチャレンジのXP乗算器をチェック
        try:
            multiplier = await self.repository.get_challenge_xp_multiplier(user_id)
            if multiplier and multiplier > 1.0:
                amount = int(amount * multiplier)
        except Exception:
            logger.warning("チャレンジXP乗算器の取得に失敗", exc_info=True)

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

    async def get_streak_details(self, user_id: int) -> dict | None:
        """連続学習の詳細情報を取得"""
        details = await self.repository.get_streak_details(user_id)
        if not details:
            return None

        streak = details["streak_days"]
        best = details["best_streak"]

        # マイルストーン計算 (7, 14, 30, 60, 100)
        milestones = [7, 14, 30, 60, 100]
        next_milestone = None
        for m in milestones:
            if streak < m:
                next_milestone = m
                break

        days_until = (next_milestone - streak) if next_milestone else 0

        return {
            "streak_days": streak,
            "best_streak": best,
            "last_study_date": details["last_study_date"],
            "next_milestone": next_milestone,
            "days_until_milestone": days_until,
        }

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

    # --- 離脱検知 ---

    async def get_churned_users(
        self, min_streak: int = 10, inactive_days: int = 2
    ) -> list[dict]:
        """ストリーク後に学習が途絶えたユーザーを取得"""
        return await self.repository.get_churned_users(min_streak, inactive_days)

    # --- フォーカススコア ---

    async def calculate_focus_score(self, user_id: int) -> dict:
        """フォーカススコアを計算 (0-100)"""
        data = await self.repository.get_focus_score_data(user_id)

        # セッション完了率 (ポモドーロ + フォーカス)
        if data["session_total"] > 0:
            completion_rate = data["session_completed"] / data["session_total"]
        else:
            completion_rate = 0.0

        # ロック成功率
        if data["lock_total"] > 0:
            lock_success = data["lock_completed"] / data["lock_total"]
        else:
            lock_success = 0.0

        # 学習一貫性
        if data["period_days"] > 0:
            consistency = data["study_days"] / data["period_days"]
        else:
            consistency = 0.0

        # セッション質 (完了率を再利用、データが十分あれば)
        session_quality = completion_rate

        score = int(
            completion_rate * 35
            + lock_success * 25
            + consistency * 25
            + session_quality * 15
        )
        score = min(100, max(0, score))

        grade = "D"
        for threshold, g in FOCUS_SCORE_GRADES:
            if score >= threshold:
                grade = g
                break

        return {
            "score": score,
            "grade": grade,
            "components": {
                "completion_rate": round(completion_rate * 100),
                "lock_success": round(lock_success * 100),
                "consistency": round(consistency * 100),
                "session_quality": round(session_quality * 100),
            },
        }

    # --- 自己ベスト ---

    async def check_personal_bests(self, user_id: int) -> dict:
        """学習記録後に自己ベスト更新をチェック"""
        level_info = await self.repository.get_user_level(user_id)
        if not level_info:
            return {}

        streak = level_info.get("streak_days", 0)
        daily = await self.repository.get_today_study_minutes(user_id)
        weekly = await self.repository.get_week_study_minutes(user_id)

        return await self.repository.update_personal_bests(
            user_id,
            streak=streak,
            daily_minutes=daily,
            weekly_minutes=weekly,
        )

    async def get_personal_bests(self, user_id: int) -> dict:
        """自己ベスト記録を取得"""
        return await self.repository.get_personal_bests(user_id)

    # --- シーズンパス ---

    async def get_active_season(self) -> dict | None:
        """アクティブなシーズンを取得"""
        return await self.repository.get_active_season()

    async def get_season_progress(self, user_id: int) -> dict | None:
        """現在のシーズン進捗を取得"""
        season = await self.repository.get_active_season()
        if not season:
            return None

        progress = await self.repository.get_season_progress(user_id, season["id"])
        if not progress:
            return {
                "season": season,
                "total_xp": 0,
                "tier": 0,
                "next_tier": SEASON_TIERS[0] if SEASON_TIERS else None,
                "tiers": SEASON_TIERS,
            }

        current_tier = progress["tier"]
        next_tier = None
        for t in SEASON_TIERS:
            if t["tier"] > current_tier:
                next_tier = t
                break

        return {
            "season": season,
            "total_xp": progress["total_xp"],
            "tier": current_tier,
            "next_tier": next_tier,
            "tiers": SEASON_TIERS,
        }

    async def add_season_xp(self, user_id: int, xp_amount: int) -> dict | None:
        """シーズンXPを追加し、ティアアップをチェック"""
        season = await self.repository.get_active_season()
        if not season:
            return None

        progress = await self.repository.upsert_season_progress(
            user_id, season["id"], xp_amount
        )
        if not progress:
            return None

        # ティアアップチェック
        total_xp = progress["total_xp"]
        current_tier = progress["tier"]
        new_tier = current_tier

        for t in SEASON_TIERS:
            if total_xp >= t["xp_required"] and t["tier"] > new_tier:
                new_tier = t["tier"]

        tier_ups = []
        if new_tier > current_tier:
            await self.repository.update_season_tier(user_id, season["id"], new_tier)
            for t in SEASON_TIERS:
                if current_tier < t["tier"] <= new_tier:
                    tier_ups.append(t)

        return {
            "total_xp": total_xp,
            "old_tier": current_tier,
            "new_tier": new_tier,
            "tier_ups": tier_ups,
        }

    async def get_season_leaderboard(self, limit: int = 10) -> list[dict]:
        season = await self.repository.get_active_season()
        if not season:
            return []
        return await self.repository.get_season_leaderboard(season["id"], limit)

    # --- 学習タイミング分析 ---

    async def get_optimal_timing(self, user_id: int) -> dict:
        """最適な学習タイミングを分析"""
        data = await self.repository.get_study_timing_data(user_id)

        dow_names = ["日", "月", "火", "水", "木", "金", "土"]

        # 最も学習量が多い時間帯 TOP3
        hourly = sorted(data["hourly"], key=lambda x: x["total_minutes"], reverse=True)
        best_hours = []
        for h in hourly[:3]:
            hour = int(h["hour"])
            best_hours.append({
                "hour": hour,
                "label": f"{hour}:00〜{hour + 1}:00",
                "total_minutes": int(h["total_minutes"]),
                "sessions": int(h["session_count"]),
            })

        # 最も学習量が多い曜日 TOP3
        daily = sorted(data["daily"], key=lambda x: x["total_minutes"], reverse=True)
        best_days = []
        for d in daily[:3]:
            dow = int(d["dow"])
            best_days.append({
                "dow": dow,
                "label": f"{dow_names[dow]}曜日",
                "total_minutes": int(d["total_minutes"]),
                "sessions": int(d["session_count"]),
            })

        # 推奨ポモドーロ時間
        avg_pomo = data["avg_pomo_minutes"]
        if avg_pomo > 0:
            # 実績ベースで推奨
            recommended_pomo = max(15, min(60, round(avg_pomo / 5) * 5))
        else:
            recommended_pomo = 25  # デフォルト

        has_data = len(hourly) > 0

        return {
            "has_data": has_data,
            "best_hours": best_hours,
            "best_days": best_days,
            "recommended_pomo_minutes": recommended_pomo,
            "avg_pomo_minutes": round(avg_pomo, 1),
            "total_completed_pomos": data["total_completed_pomos"],
        }
