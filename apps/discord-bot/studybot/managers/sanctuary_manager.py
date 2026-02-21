"""サンクチュアリ（癒しの学習庭園）ビジネスロジック"""

import logging
from datetime import UTC, datetime

from studybot.repositories.sanctuary_repository import SanctuaryRepository

logger = logging.getLogger(__name__)

# 植物タイプ定義
PLANT_TYPES = {
    "sakura": {"name": "桜", "emoji": "🌸", "description": "美しい桜の木"},
    "sunflower": {"name": "ひまわり", "emoji": "🌻", "description": "明るいひまわり"},
    "bamboo": {"name": "竹", "emoji": "🎋", "description": "力強い竹"},
    "lotus": {"name": "蓮", "emoji": "🪷", "description": "静かな蓮の花"},
    "pine": {"name": "松", "emoji": "🌲", "description": "常緑の松"},
    "maple": {"name": "紅葉", "emoji": "🍁", "description": "色づく紅葉"},
    "lavender": {"name": "ラベンダー", "emoji": "💜", "description": "癒しのラベンダー"},
    "rose": {"name": "薔薇", "emoji": "🌹", "description": "優雅な薔薇"},
}

# 成長段階
GROWTH_STAGES = [
    {"name": "種", "emoji": "🌰", "min": 0, "max": 20},
    {"name": "芽", "emoji": "🌱", "min": 21, "max": 50},
    {"name": "若木", "emoji": "🌿", "min": 51, "max": 80},
    {"name": "樹木", "emoji": "🌳", "min": 81, "max": 95},
    {"name": "開花", "emoji": "🌺", "min": 96, "max": 100},
]

# 自然サイクルフェーズ
PHASES = {
    "sunrise": {"name": "日の出", "emoji": "🌅", "bonus": 8, "hours": (5, 9)},
    "midday": {"name": "真昼", "emoji": "☀️", "bonus": 5, "hours": (9, 15)},
    "sunset": {"name": "夕暮れ", "emoji": "🌇", "bonus": 5, "hours": (15, 20)},
    "nightfall": {"name": "夜", "emoji": "🌙", "bonus": 10, "hours": (20, 5)},
}

MAX_PLANTS = 12


class SanctuaryManager:
    """庭園成長・植物管理・セッション管理"""

    def __init__(self, db_pool) -> None:
        self.repository = SanctuaryRepository(db_pool)

    async def ensure_garden(self, user_id: int) -> dict:
        """庭園を取得、なければ作成"""
        garden = await self.repository.get_garden(user_id)
        if not garden:
            garden = await self.repository.create_garden(user_id)
        return garden

    async def get_garden_view(self, user_id: int) -> dict:
        """庭園の表示データを構築"""
        garden = await self.ensure_garden(user_id)
        plants = await self.repository.get_plants(user_id)
        stats = await self.repository.get_session_stats(user_id)

        # 各植物の成長段階を計算
        for plant in plants:
            plant["stage"] = self._get_growth_stage(plant["growth"])

        # 庭園活力 = 全植物の平均健康度
        if plants:
            garden["vitality"] = sum(p["health"] for p in plants) / len(plants)
        else:
            garden["vitality"] = 0

        return {
            "garden": garden,
            "plants": plants,
            "stats": stats,
            "phase": self._get_current_phase(),
        }

    async def plant_seed(self, user_id: int, plant_type: str, name: str = "") -> dict | None:
        """新しい種を植える"""
        if plant_type not in PLANT_TYPES:
            return None

        count = await self.repository.count_plants(user_id)
        if count >= MAX_PLANTS:
            return None

        await self.ensure_garden(user_id)
        plant_info = PLANT_TYPES[plant_type]
        if not name:
            name = plant_info["name"]

        return await self.repository.plant_seed(user_id, plant_type, name)

    async def tend_garden(self, user_id: int) -> dict:
        """庭の手入れ: 全植物の健康度を回復"""
        plants = await self.repository.get_plants(user_id)
        tended = []
        for plant in plants:
            new_health = min(100.0, plant["health"] + 10)
            if new_health != plant["health"]:
                await self.repository.update_plant(plant["id"], plant["growth"], new_health)
                tended.append(
                    {
                        "name": plant["name"],
                        "type": plant["plant_type"],
                        "health_before": plant["health"],
                        "health_after": new_health,
                    }
                )

        await self.repository.update_garden_last_tended(user_id)
        return {"tended": tended, "count": len(tended)}

    async def start_session(self, user_id: int, mood: int, energy: int) -> dict | None:
        """自然サイクルセッション開始"""
        # 既存セッションチェック
        active = await self.repository.get_active_session(user_id)
        if active:
            return None

        await self.ensure_garden(user_id)
        phase = self._get_current_phase()
        return await self.repository.create_session(user_id, phase, mood, energy)

    async def complete_session(
        self,
        user_id: int,
        mood_after: int,
        energy_after: int,
        duration_minutes: int,
        note: str = "",
    ) -> dict | None:
        """セッション完了: 成長ポイント計算"""
        session = await self.repository.get_active_session(user_id)
        if not session:
            return None

        growth_points = self._calculate_growth_points(
            duration_minutes=duration_minutes,
            mood_before=session["mood_before"],
            mood_after=mood_after,
            phase=session["phase"],
            had_yesterday=await self.repository.had_session_yesterday(user_id),
            stress=3,  # Default stress if not provided
        )

        await self.repository.complete_session(
            session["id"], mood_after, energy_after, growth_points, note
        )

        # 植物に成長ポイントを分配
        plants = await self.repository.get_plants(user_id)
        growth_per_plant = growth_points / max(len(plants), 1)
        grown_plants = []
        for plant in plants:
            if plant["health"] > 0:
                new_growth = min(100.0, plant["growth"] + growth_per_plant)
                await self.repository.update_plant(plant["id"], new_growth, plant["health"])
                if new_growth != plant["growth"]:
                    old_stage = self._get_growth_stage(plant["growth"])
                    new_stage = self._get_growth_stage(new_growth)
                    grown_plants.append(
                        {
                            "name": plant["name"],
                            "growth": new_growth,
                            "stage": new_stage,
                            "evolved": old_stage["name"] != new_stage["name"],
                        }
                    )

        return {
            "session": session,
            "growth_points": growth_points,
            "grown_plants": grown_plants,
            "duration": duration_minutes,
        }

    async def award_growth_from_study(self, user_id: int, minutes: int) -> float:
        """外部学習からの成長ポイント付与（gamificationフック用）"""
        garden = await self.repository.get_garden(user_id)
        if not garden:
            return 0.0

        base = min(minutes, 60)
        consistency = 10 if await self.repository.had_session_yesterday(user_id) else 0
        growth = (base + consistency) * 0.5  # 外部学習は半分の成長

        plants = await self.repository.get_plants(user_id)
        if not plants:
            return growth

        per_plant = growth / len(plants)
        for plant in plants:
            if plant["health"] > 0:
                new_growth = min(100.0, plant["growth"] + per_plant)
                await self.repository.update_plant(plant["id"], new_growth, plant["health"])
        return growth

    async def daily_update(self) -> dict:
        """日次更新: 植物健康度減衰"""
        decayed = await self.repository.decay_plants(48)
        return {"decayed_plants": decayed}

    async def get_stats(self, user_id: int) -> dict:
        """セルフケア統計"""
        stats = await self.repository.get_session_stats(user_id)
        garden = await self.ensure_garden(user_id)
        plants = await self.repository.get_plants(user_id)
        return {
            "stats": stats,
            "garden": garden,
            "plant_count": len(plants),
            "healthy_plants": sum(1 for p in plants if p["health"] > 50),
        }

    # --- 内部メソッド ---

    def _calculate_growth_points(
        self,
        duration_minutes: int,
        mood_before: int,
        mood_after: int,
        phase: str,
        had_yesterday: bool,
        stress: int = 3,
    ) -> float:
        """成長ポイント計算"""
        base = min(duration_minutes, 60)
        mood_bonus = max(0, (mood_after - mood_before) * 5)
        consistency_bonus = 10 if had_yesterday else 0
        phase_bonus = PHASES.get(phase, {}).get("bonus", 5)
        wellness_mult = 1.0 + (5 - stress) * 0.05
        return (base + mood_bonus + consistency_bonus + phase_bonus) * wellness_mult

    def _get_current_phase(self) -> str:
        """現在の自然サイクルフェーズを取得"""
        hour = datetime.now(UTC).hour + 9  # JST
        hour = hour % 24
        for key, phase in PHASES.items():
            start, end = phase["hours"]
            if start < end:
                if start <= hour < end:
                    return key
            else:  # nightfall wraps around midnight
                if hour >= start or hour < end:
                    return key
        return "midday"

    def _get_growth_stage(self, growth: float) -> dict:
        """成長値から段階を取得"""
        for stage in GROWTH_STAGES:
            if stage["min"] <= growth <= stage["max"]:
                return stage
        return GROWTH_STAGES[-1]
