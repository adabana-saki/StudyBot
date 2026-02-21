"""エクスペディション（知識探検冒険）のテスト"""

import pytest

from studybot.managers.expedition_manager import (
    DEFAULT_TERRITORIES,
    DISCOVERY_TEMPLATES,
    EXPLORER_RANKS,
    REGION_CATEGORY_MAP,
    REGIONS,
    TERRITORY_PLANT_MAP,
    ExpeditionManager,
)


@pytest.fixture
def expedition_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = ExpeditionManager(pool)
    return manager, conn


# --- ランク計算テスト ---


class TestRankCalculation:
    def test_rank_beginner(self, expedition_manager):
        manager, _ = expedition_manager
        rank = manager._get_rank(0)
        assert rank["name"] == "見習い探検家"

    def test_rank_scout(self, expedition_manager):
        manager, _ = expedition_manager
        rank = manager._get_rank(3)
        assert rank["name"] == "偵察兵"

    def test_rank_pathfinder(self, expedition_manager):
        manager, _ = expedition_manager
        rank = manager._get_rank(8)
        assert rank["name"] == "探路者"

    def test_rank_ranger(self, expedition_manager):
        manager, _ = expedition_manager
        rank = manager._get_rank(15)
        assert rank["name"] == "レンジャー"

    def test_rank_cartographer(self, expedition_manager):
        manager, _ = expedition_manager
        rank = manager._get_rank(25)
        assert rank["name"] == "地図製作者"

    def test_rank_legend(self, expedition_manager):
        manager, _ = expedition_manager
        rank = manager._get_rank(40)
        assert rank["name"] == "伝説の探検家"

    def test_rank_intermediate(self, expedition_manager):
        manager, _ = expedition_manager
        rank = manager._get_rank(5)
        assert rank["name"] == "偵察兵"  # 3以上8未満


# --- 探検家管理テスト ---


class TestExplorerManagement:
    @pytest.mark.asyncio
    async def test_ensure_explorer_creates_new(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.side_effect = [
            None,  # get_explorer
            {"user_id": 123, "total_territories": 0, "total_points": 0},  # create_explorer
        ]

        explorer = await manager.ensure_explorer(123)
        assert explorer["user_id"] == 123
        assert explorer["total_territories"] == 0

    @pytest.mark.asyncio
    async def test_ensure_explorer_returns_existing(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "user_id": 123,
            "total_territories": 5,
            "total_points": 50,
        }

        explorer = await manager.ensure_explorer(123)
        assert explorer["total_territories"] == 5


# --- 学習記録テスト ---


class TestStudyRecording:
    @pytest.mark.asyncio
    async def test_record_study_with_matching_territory(self, expedition_manager):
        manager, conn = expedition_manager
        # get_territory_by_keyword
        conn.fetchrow.side_effect = [
            {
                "id": 1,
                "name": "算数の丘",
                "region": "mountains",
                "topic_keyword": "算数",
                "difficulty": 1,
                "required_minutes": 60,
                "emoji": "🧮",
            },
            # ensure_explorer -> get_explorer
            {"user_id": 123, "total_territories": 0, "total_points": 0},
            # add_progress
            {"id": 1, "user_id": 123, "territory_id": 1, "minutes_spent": 30, "completed": False},
            # get_user_active_party
            None,
        ]

        result = await manager.record_study(123, "算数", 30)
        assert result is not None
        assert result["minutes_added"] == 30
        assert result["completed_now"] is False

    @pytest.mark.asyncio
    async def test_record_study_completes_territory(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.side_effect = [
            # get_territory_by_keyword
            {
                "id": 1,
                "name": "算数の丘",
                "region": "mountains",
                "topic_keyword": "算数",
                "difficulty": 1,
                "required_minutes": 60,
                "emoji": "🧮",
            },
            # ensure_explorer -> get_explorer
            {"user_id": 123, "total_territories": 0, "total_points": 0},
            # add_progress (accumulated enough)
            {"id": 1, "user_id": 123, "territory_id": 1, "minutes_spent": 60, "completed": False},
            # get_user_active_party
            None,
        ]
        conn.fetchval.return_value = 1  # count_completed
        conn.execute.return_value = None

        result = await manager.record_study(123, "算数", 30)
        assert result is not None
        assert result["completed_now"] is True

    @pytest.mark.asyncio
    async def test_record_study_no_matching_territory(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = None  # no territory match

        result = await manager.record_study(123, "未知の科目", 30)
        assert result is None

    @pytest.mark.asyncio
    async def test_record_study_empty_topic(self, expedition_manager):
        manager, conn = expedition_manager
        result = await manager.record_study(123, "", 30)
        assert result is None

    @pytest.mark.asyncio
    async def test_record_study_zero_minutes(self, expedition_manager):
        manager, conn = expedition_manager
        result = await manager.record_study(123, "数学", 0)
        assert result is None

    @pytest.mark.asyncio
    async def test_record_study_with_party(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.side_effect = [
            # get_territory_by_keyword
            {
                "id": 1,
                "name": "算数の丘",
                "region": "mountains",
                "topic_keyword": "算数",
                "difficulty": 1,
                "required_minutes": 60,
                "emoji": "🧮",
            },
            # ensure_explorer -> get_explorer
            {"user_id": 123, "total_territories": 0, "total_points": 0},
            # add_progress
            {"id": 1, "user_id": 123, "territory_id": 1, "minutes_spent": 30, "completed": False},
            # get_user_active_party
            {
                "id": 10,
                "name": "テストパーティ",
                "region": "mountains",
                "goal_minutes": 100,
                "progress_minutes": 50,
                "status": "active",
            },
            # get_party (after contribution)
            {
                "id": 10,
                "name": "テストパーティ",
                "region": "mountains",
                "goal_minutes": 100,
                "progress_minutes": 80,
                "status": "active",
            },
        ]
        conn.execute.return_value = None

        result = await manager.record_study(123, "算数", 30)
        assert result is not None


# --- マップ表示テスト ---


class TestMapDisplay:
    @pytest.mark.asyncio
    async def test_get_map_empty(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "user_id": 123,
            "total_territories": 0,
            "total_points": 0,
        }
        conn.fetch.side_effect = [
            [],  # get_territories
            [],  # get_all_progress
        ]

        map_data = await manager.get_map(123)
        assert isinstance(map_data, dict)

    @pytest.mark.asyncio
    async def test_get_map_with_progress(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "user_id": 123,
            "total_territories": 1,
            "total_points": 10,
        }
        conn.fetch.side_effect = [
            [  # get_territories
                {
                    "id": 1,
                    "name": "算数の丘",
                    "region": "mountains",
                    "topic_keyword": "算数",
                    "difficulty": 1,
                    "required_minutes": 60,
                    "emoji": "🧮",
                },
            ],
            [  # get_all_progress
                {
                    "territory_id": 1,
                    "minutes_spent": 30,
                    "completed": False,
                    "territory_name": "算数の丘",
                    "region": "mountains",
                    "required_minutes": 60,
                    "emoji": "🧮",
                    "topic_keyword": "算数",
                },
            ],
        ]

        map_data = await manager.get_map(123)
        assert "mountains" in map_data
        assert map_data["mountains"]["territories"][0]["progress_pct"] == 50


# --- パーティ管理テスト ---


class TestPartyManagement:
    @pytest.mark.asyncio
    async def test_create_party_success(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.side_effect = [
            None,  # get_user_active_party
            {
                "id": 1,
                "creator_id": 123,
                "guild_id": 456,
                "name": "冒険隊",
                "region": "mountains",
                "goal_minutes": 100,
                "progress_minutes": 0,
                "status": "active",
            },
        ]
        conn.execute.return_value = None

        party = await manager.create_party(123, 456, "冒険隊", "mountains", 100)
        assert party is not None
        assert party["name"] == "冒険隊"

    @pytest.mark.asyncio
    async def test_create_party_invalid_region(self, expedition_manager):
        manager, conn = expedition_manager
        result = await manager.create_party(123, 456, "冒険隊", "invalid", 100)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_party_invalid_goal(self, expedition_manager):
        manager, conn = expedition_manager
        result = await manager.create_party(123, 456, "冒険隊", "mountains", 10)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_party_already_in_party(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "name": "既存パーティ",
            "status": "active",
        }

        result = await manager.create_party(123, 456, "冒険隊", "mountains", 100)
        assert result is None

    @pytest.mark.asyncio
    async def test_join_party_success(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.side_effect = [
            # get_party
            {"id": 1, "name": "冒険隊", "status": "active", "goal_minutes": 100},
            # get_user_active_party
            None,
        ]
        conn.fetch.return_value = [
            {"user_id": 111},
            {"user_id": 222},
        ]  # party members < 5
        conn.execute.return_value = None

        result = await manager.join_party(789, 1)
        assert result is True

    @pytest.mark.asyncio
    async def test_join_party_full(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "name": "冒険隊",
            "status": "active",
            "goal_minutes": 100,
        }
        conn.fetch.return_value = [{"user_id": i} for i in range(5)]  # full party

        result = await manager.join_party(789, 1)
        assert result is False

    @pytest.mark.asyncio
    async def test_join_party_not_active(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "name": "冒険隊",
            "status": "completed",
        }

        result = await manager.join_party(789, 1)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_party_status_none(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = None

        result = await manager.get_party_status(123)
        assert result is None


# --- 探検家プロフィールテスト ---


class TestExplorerProfile:
    @pytest.mark.asyncio
    async def test_get_profile(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "user_id": 123,
            "total_territories": 5,
            "total_points": 50,
        }
        conn.fetchval.return_value = 5  # count_completed
        conn.fetch.return_value = []  # progress

        profile = await manager.get_explorer_profile(123)
        assert profile["rank"]["name"] == "偵察兵"
        assert profile["completed_territories"] == 5


# --- 発見イベントテスト ---


class TestDiscoveryEvents:
    @pytest.mark.asyncio
    async def test_generate_discovery(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "guild_id": 456,
            "title": "テスト発見",
            "description": "テスト説明",
            "reward_points": 50,
        }

        event = await manager.generate_discovery(456)
        assert event is not None

    @pytest.mark.asyncio
    async def test_get_discovery(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "guild_id": 456,
            "title": "テスト発見",
            "description": "テスト説明",
            "reward_points": 50,
        }

        event = await manager.get_discovery(456)
        assert event["title"] == "テスト発見"


# --- 定数テスト ---


class TestConstants:
    def test_regions_defined(self):
        assert len(REGIONS) >= 6
        for _key, val in REGIONS.items():
            assert "name" in val
            assert "emoji" in val

    def test_default_territories_defined(self):
        assert len(DEFAULT_TERRITORIES) >= 20
        for t in DEFAULT_TERRITORIES:
            assert len(t) == 6  # name, region, keyword, diff, minutes, emoji

    def test_explorer_ranks_ordered(self):
        prev = -1
        for rank in EXPLORER_RANKS:
            assert rank["min_territories"] > prev
            prev = rank["min_territories"]

    def test_discovery_templates_defined(self):
        assert len(DISCOVERY_TEMPLATES) >= 5
        for t in DISCOVERY_TEMPLATES:
            assert "title" in t
            assert "description" in t
            assert "reward" in t

    def test_region_category_map_valid(self):
        for region, category in REGION_CATEGORY_MAP.items():
            assert region in REGIONS
            from studybot.managers.forge_manager import SKILL_CATEGORIES

            assert category in SKILL_CATEGORIES

    def test_territory_plant_map_covers_regions(self):
        for region in REGIONS:
            assert region in TERRITORY_PLANT_MAP


# --- 探検日誌テスト ---


class TestJournal:
    @pytest.mark.asyncio
    async def test_save_journal_entry(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "user_id": 123,
            "title": "今日の発見",
            "content": "数学の面白さを知った",
        }

        entry = await manager.save_journal_entry(123, "今日の発見", "数学の面白さを知った")
        assert entry["title"] == "今日の発見"

    @pytest.mark.asyncio
    async def test_get_journal_entries_empty(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetch.return_value = []

        entries = await manager.get_journal_entries(123)
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_journal_entries_with_data(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 123,
                "title": "日誌1",
                "content": "内容1",
                "created_at": "2026-02-21",
            },
            {
                "id": 2,
                "user_id": 123,
                "title": "日誌2",
                "content": "内容2",
                "created_at": "2026-02-20",
            },
        ]

        entries = await manager.get_journal_entries(123)
        assert len(entries) == 2


# --- 領域完了報酬テスト ---


class TestRewards:
    def test_rewards_difficulty_1(self, expedition_manager):
        manager, _ = expedition_manager
        rewards = manager.get_territory_completion_rewards({"difficulty": 1, "region": "mountains"})
        assert rewards["xp"] == 50
        assert rewards["coins"] == 20

    def test_rewards_difficulty_3(self, expedition_manager):
        manager, _ = expedition_manager
        rewards = manager.get_territory_completion_rewards({"difficulty": 3, "region": "forest"})
        assert rewards["xp"] == 150
        assert rewards["coins"] == 60

    def test_rewards_difficulty_5(self, expedition_manager):
        manager, _ = expedition_manager
        rewards = manager.get_territory_completion_rewards({"difficulty": 5, "region": "sky"})
        assert rewards["xp"] == 250
        assert rewards["coins"] == 100

    @pytest.mark.asyncio
    async def test_record_study_returns_rewards(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.side_effect = [
            # get_territory_by_keyword
            {
                "id": 1,
                "name": "算数の丘",
                "region": "mountains",
                "topic_keyword": "算数",
                "difficulty": 1,
                "required_minutes": 60,
                "emoji": "🧮",
            },
            # ensure_explorer -> get_explorer
            {"user_id": 123, "total_territories": 0, "total_points": 0},
            # add_progress (complete)
            {"id": 1, "user_id": 123, "territory_id": 1, "minutes_spent": 60, "completed": False},
            # get_user_active_party
            None,
        ]
        conn.fetchval.return_value = 1
        conn.execute.return_value = None

        result = await manager.record_study(123, "算数", 30)
        assert result["completed_now"] is True
        assert result["rewards"] is not None
        assert result["rewards"]["xp"] == 50
        assert result["rewards"]["coins"] == 20

    @pytest.mark.asyncio
    async def test_record_study_no_rewards_incomplete(self, expedition_manager):
        manager, conn = expedition_manager
        conn.fetchrow.side_effect = [
            {
                "id": 1,
                "name": "算数の丘",
                "region": "mountains",
                "topic_keyword": "算数",
                "difficulty": 1,
                "required_minutes": 60,
                "emoji": "🧮",
            },
            {"user_id": 123, "total_territories": 0, "total_points": 0},
            {"id": 1, "user_id": 123, "territory_id": 1, "minutes_spent": 30, "completed": False},
            None,
        ]

        result = await manager.record_study(123, "算数", 30)
        assert result["completed_now"] is False
        assert result["rewards"] is None


# --- 相互連携テスト ---


class TestCrossConceptExpedition:
    def test_territory_access_low_difficulty(self, expedition_manager):
        """難易度3以下はmastery制限なし（Cog層で判定）"""
        manager, _ = expedition_manager
        # 直接テストできないが、定数が正しいことを確認
        assert REGION_CATEGORY_MAP["mountains"] == "math"
        assert REGION_CATEGORY_MAP["sky"] == "programming"

    def test_plant_map_keys_match_regions(self, expedition_manager):
        """植物マップが全地域をカバー"""
        for region in REGIONS:
            assert region in TERRITORY_PLANT_MAP
            assert isinstance(TERRITORY_PLANT_MAP[region], str)
