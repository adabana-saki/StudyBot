"""エクスペディション（知識探検冒険）ビジネスロジック"""

import logging
from datetime import datetime, timedelta, timezone

from studybot.repositories.expedition_repository import ExpeditionRepository

logger = logging.getLogger(__name__)

# マップ地域定義
REGIONS = {
    "mountains": {"name": "数理の山脈", "emoji": "🏔️", "description": "数学と論理の峰々"},
    "forest": {"name": "言語の森", "emoji": "🌲", "description": "言語と文学の深い森"},
    "ocean": {"name": "科学の大海", "emoji": "🌊", "description": "自然科学の広大な海"},
    "desert": {"name": "歴史の砂漠", "emoji": "🏜️", "description": "歴史と文明の遺跡"},
    "sky": {"name": "技術の空", "emoji": "🌌", "description": "プログラミングと技術の空域"},
    "plains": {"name": "芸術の平原", "emoji": "🏞️", "description": "芸術と創造の草原"},
}

# デフォルト領域データ
DEFAULT_TERRITORIES = [
    ("算数の丘", "mountains", "算数", 1, 60, "🧮"),
    ("代数の峠", "mountains", "代数", 2, 120, "📐"),
    ("幾何の頂", "mountains", "幾何", 2, 120, "📏"),
    ("解析の氷壁", "mountains", "解析", 3, 240, "📈"),
    ("統計の展望台", "mountains", "統計", 3, 180, "📊"),
    ("英語の小道", "forest", "英語", 1, 60, "🔤"),
    ("文法の泉", "forest", "文法", 2, 120, "📖"),
    ("読解の大樹", "forest", "読解", 2, 120, "📚"),
    ("作文の花園", "forest", "作文", 3, 180, "✍️"),
    ("古典の聖域", "forest", "古典", 3, 240, "📜"),
    ("物理の波打ち際", "ocean", "物理", 2, 120, "⚛️"),
    ("化学の珊瑚礁", "ocean", "化学", 2, 120, "🧪"),
    ("生物の海底洞窟", "ocean", "生物", 2, 120, "🧬"),
    ("地学の海溝", "ocean", "地学", 3, 180, "🌍"),
    ("日本史の遺跡", "desert", "日本史", 2, 120, "🏯"),
    ("世界史のオアシス", "desert", "世界史", 2, 120, "🗺️"),
    ("公民の交差路", "desert", "公民", 2, 120, "⚖️"),
    ("経済の市場", "desert", "経済", 3, 180, "💰"),
    ("プログラミング入門の滑走路", "sky", "プログラミング", 1, 60, "💻"),
    ("アルゴリズムの雲海", "sky", "アルゴリズム", 3, 240, "☁️"),
    ("データベースの衛星", "sky", "データベース", 3, 180, "🛰️"),
    ("美術の草原", "plains", "美術", 1, 60, "🎨"),
    ("音楽の丘", "plains", "音楽", 1, 60, "🎵"),
    ("体育のフィールド", "plains", "体育", 1, 60, "⚽"),
]

# 探検家ランク
EXPLORER_RANKS = [
    {"name": "見習い探検家", "emoji": "🥾", "min_territories": 0},
    {"name": "偵察兵", "emoji": "🔭", "min_territories": 3},
    {"name": "探路者", "emoji": "🧭", "min_territories": 8},
    {"name": "レンジャー", "emoji": "🗺️", "min_territories": 15},
    {"name": "地図製作者", "emoji": "📜", "min_territories": 25},
    {"name": "伝説の探検家", "emoji": "👑", "min_territories": 40},
]

# 発見イベントテンプレート
DISCOVERY_TEMPLATES = [
    {
        "title": "失われた文献の発見",
        "description": "古代の知恵が詰まった文献を発見！60分の学習で解読完了",
        "reward": 50,
    },
    {
        "title": "隠された遺跡",
        "description": "未知の遺跡を発見！90分の探索で秘密を解明",
        "reward": 75,
    },
    {
        "title": "星座の地図",
        "description": "夜空に浮かぶ知識の星座を記録！45分の観測で完了",
        "reward": 40,
    },
    {
        "title": "古代の暗号",
        "description": "謎の暗号文を解読せよ！数学と言語の知識が必要",
        "reward": 60,
    },
    {
        "title": "生態系の調査",
        "description": "未知の生態系を調査！科学的観察力が試される",
        "reward": 55,
    },
    {
        "title": "伝説の図書館",
        "description": "伝説の図書館への道を開け！120分の集中学習が鍵",
        "reward": 100,
    },
]


# 地域→スキルカテゴリ マッピング (Forge連携)
REGION_CATEGORY_MAP = {
    "mountains": "math",
    "forest": "english",
    "ocean": "science",
    "desert": "history",
    "sky": "programming",
    "plains": "art",
}

# 領域完了→サンクチュアリ植物 マッピング
TERRITORY_PLANT_MAP = {
    "mountains": "pine",
    "forest": "bamboo",
    "ocean": "lotus",
    "desert": "sunflower",
    "sky": "lavender",
    "plains": "rose",
}


class ExpeditionManager:
    """マップ進捗・パーティ管理・発見イベント"""

    def __init__(self, db_pool) -> None:
        self.repository = ExpeditionRepository(db_pool)

    async def ensure_explorer(self, user_id: int) -> dict:
        """探検家プロフィールを取得/作成"""
        explorer = await self.repository.get_explorer(user_id)
        if not explorer:
            explorer = await self.repository.create_explorer(user_id)
        return explorer

    async def seed_territories(self) -> int:
        """デフォルト領域データを投入"""
        count = 0
        for name, region, keyword, diff, minutes, emoji in DEFAULT_TERRITORIES:
            await self.repository.upsert_territory(name, region, keyword, diff, minutes, emoji)
            count += 1
        return count

    async def get_map(self, user_id: int, region: str = "") -> dict:
        """ワールドマップの表示データ"""
        await self.ensure_explorer(user_id)
        territories = await self.repository.get_territories(region)
        progress = await self.repository.get_all_progress(user_id)
        progress_map = {p["territory_id"]: p for p in progress}

        map_data = {}
        for t in territories:
            r = t["region"]
            if r not in map_data:
                region_info = REGIONS.get(r, {"name": r, "emoji": "🗺️"})
                map_data[r] = {
                    "name": region_info["name"],
                    "emoji": region_info["emoji"],
                    "territories": [],
                    "completed": 0,
                    "total": 0,
                }
            p = progress_map.get(t["id"], {})
            pct = (
                min(100, int(p.get("minutes_spent", 0) / t["required_minutes"] * 100))
                if t["required_minutes"] > 0
                else 0
            )
            map_data[r]["territories"].append(
                {
                    **t,
                    "progress_pct": pct,
                    "minutes_spent": p.get("minutes_spent", 0),
                    "completed": p.get("completed", False),
                }
            )
            map_data[r]["total"] += 1
            if p.get("completed"):
                map_data[r]["completed"] += 1

        return map_data

    async def record_study(self, user_id: int, topic: str, minutes: int) -> dict | None:
        """学習をマップ進捗に反映"""
        if not topic or minutes <= 0:
            return None

        territory = await self.repository.get_territory_by_keyword(topic)
        if not territory:
            return None

        await self.ensure_explorer(user_id)
        result = await self.repository.add_progress(user_id, territory["id"], minutes)

        completed_now = False
        if (
            result
            and not result.get("completed")
            and result["minutes_spent"] >= territory["required_minutes"]
        ):
            await self.repository.mark_completed(user_id, territory["id"])
            completed_now = True
            # 探検家統計更新
            total = await self.repository.count_completed(user_id)
            await self.repository.update_explorer(user_id, total, total * 10)

        # パーティ貢献
        party = await self.repository.get_user_active_party(user_id)
        if party:
            await self.repository.add_party_contribution(party["id"], user_id, minutes)
            # パーティ目標達成チェック
            updated_party = await self.repository.get_party(party["id"])
            if (
                updated_party
                and updated_party["progress_minutes"] >= updated_party["goal_minutes"]
                and updated_party["status"] == "active"
            ):
                await self.repository.complete_party(party["id"])

        # 報酬計算（領域完了時）
        rewards = None
        if completed_now:
            rewards = self.get_territory_completion_rewards(territory)

        return {
            "territory": territory,
            "minutes_added": minutes,
            "total_minutes": result.get("minutes_spent", 0),
            "completed_now": completed_now,
            "required": territory["required_minutes"],
            "rewards": rewards,
        }

    async def get_explorer_profile(self, user_id: int) -> dict:
        """探検家プロフィール"""
        explorer = await self.ensure_explorer(user_id)
        completed = await self.repository.count_completed(user_id)
        rank = self._get_rank(completed)
        progress = await self.repository.get_all_progress(user_id)
        return {
            "explorer": explorer,
            "rank": rank,
            "completed_territories": completed,
            "progress": progress,
        }

    async def create_party(
        self,
        creator_id: int,
        guild_id: int,
        name: str,
        region: str,
        goal_minutes: int,
    ) -> dict | None:
        """パーティ作成"""
        if region not in REGIONS:
            return None
        if goal_minutes < 30 or goal_minutes > 10000:
            return None
        # 既にアクティブなパーティがあるか
        existing = await self.repository.get_user_active_party(creator_id)
        if existing:
            return None
        return await self.repository.create_party(creator_id, guild_id, name, region, goal_minutes)

    async def join_party(self, user_id: int, party_id: int) -> bool:
        """パーティ参加"""
        party = await self.repository.get_party(party_id)
        if not party or party["status"] != "active":
            return False
        members = await self.repository.get_party_members(party_id)
        if len(members) >= 5:
            return False
        existing = await self.repository.get_user_active_party(user_id)
        if existing:
            return False
        return await self.repository.join_party(party_id, user_id)

    async def get_party_status(self, user_id: int) -> dict | None:
        """パーティ進捗"""
        party = await self.repository.get_user_active_party(user_id)
        if not party:
            return None
        members = await self.repository.get_party_members(party["id"])
        pct = (
            min(100, int(party["progress_minutes"] / party["goal_minutes"] * 100))
            if party["goal_minutes"] > 0
            else 0
        )
        return {
            "party": party,
            "members": members,
            "progress_pct": pct,
        }

    async def get_discovery(self, guild_id: int) -> dict:
        """今週の発見イベント"""
        return await self.repository.get_active_discovery(guild_id)

    async def generate_discovery(self, guild_id: int) -> dict:
        """発見イベント生成"""
        import random

        template = random.choice(DISCOVERY_TEMPLATES)
        expires = datetime.now(timezone.utc) + timedelta(days=7)  # noqa: UP017
        return await self.repository.create_discovery(
            guild_id,
            template["title"],
            template["description"],
            template["reward"],
            expires.isoformat(),
        )

    async def check_parties(self, guild_id: int) -> list[dict]:
        """パーティ目標達成チェック"""
        parties = await self.repository.get_active_parties(guild_id)
        completed = []
        for party in parties:
            if party["progress_minutes"] >= party["goal_minutes"]:
                await self.repository.complete_party(party["id"])
                completed.append(party)
        return completed

    # --- 探検日誌 ---

    async def save_journal_entry(self, user_id: int, title: str, content: str) -> dict:
        """日誌保存"""
        return await self.repository.create_journal_entry(user_id, title, content)

    async def get_journal_entries(self, user_id: int, limit: int = 5) -> list[dict]:
        """日誌一覧取得"""
        return await self.repository.get_journal_entries(user_id, limit)

    # --- 領域完了報酬 ---

    def get_territory_completion_rewards(self, territory: dict) -> dict:
        """報酬計算: XP=difficulty*50, coins=difficulty*20"""
        difficulty = territory.get("difficulty", 1)
        return {
            "xp": difficulty * 50,
            "coins": difficulty * 20,
            "region": territory.get("region", ""),
        }

    def _get_rank(self, completed_territories: int) -> dict:
        """探検家ランクを計算"""
        rank = EXPLORER_RANKS[0]
        for r in EXPLORER_RANKS:
            if completed_territories >= r["min_territories"]:
                rank = r
        return rank
