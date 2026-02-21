"""サンクチュアリ（癒しの学習庭園）のテスト"""

import pytest

from studybot.managers.sanctuary_manager import (
    GROWTH_STAGES,
    MAX_PLANTS,
    PHASES,
    PLANT_TYPES,
    SanctuaryManager,
)


@pytest.fixture
def sanctuary_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = SanctuaryManager(pool)
    return manager, conn


# --- 成長ポイント計算テスト ---


class TestGrowthPointCalculation:
    def test_basic_growth(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        points = manager._calculate_growth_points(
            duration_minutes=30,
            mood_before=3,
            mood_after=4,
            phase="midday",
            had_yesterday=False,
            stress=3,
        )
        # base=30 + mood_bonus=5 + consistency=0 + phase=5 = 40 * 1.1(stress=3)
        assert points == pytest.approx(44.0)

    def test_growth_capped_at_60(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        points = manager._calculate_growth_points(
            duration_minutes=120,
            mood_before=3,
            mood_after=3,
            phase="midday",
            had_yesterday=False,
            stress=3,
        )
        # base=60 (capped) + 0 + 0 + 5 = 65 * 1.1
        assert points == pytest.approx(71.5)

    def test_mood_improvement_bonus(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        points = manager._calculate_growth_points(
            duration_minutes=30,
            mood_before=1,
            mood_after=5,
            phase="midday",
            had_yesterday=False,
            stress=3,
        )
        # base=30 + mood_bonus=20 + 0 + 5 = 55 * 1.1
        assert points == pytest.approx(60.5)

    def test_mood_decrease_no_penalty(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        points = manager._calculate_growth_points(
            duration_minutes=30,
            mood_before=5,
            mood_after=3,
            phase="midday",
            had_yesterday=False,
            stress=3,
        )
        # base=30 + mood_bonus=0(max(0,-10)) + 0 + 5 = 35 * 1.1
        assert points == pytest.approx(38.5)

    def test_consistency_bonus(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        points = manager._calculate_growth_points(
            duration_minutes=30,
            mood_before=3,
            mood_after=3,
            phase="midday",
            had_yesterday=True,
            stress=3,
        )
        # base=30 + 0 + consistency=10 + 5 = 45 * 1.1
        assert points == pytest.approx(49.5)

    def test_nightfall_phase_bonus(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        points = manager._calculate_growth_points(
            duration_minutes=30,
            mood_before=3,
            mood_after=3,
            phase="nightfall",
            had_yesterday=False,
            stress=3,
        )
        # base=30 + 0 + 0 + 10 = 40 * 1.1
        assert points == pytest.approx(44.0)

    def test_low_stress_multiplier(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        points = manager._calculate_growth_points(
            duration_minutes=30,
            mood_before=3,
            mood_after=3,
            phase="midday",
            had_yesterday=False,
            stress=1,
        )
        # base=30 + 0 + 0 + 5 = 35 * 1.2
        assert points == pytest.approx(42.0)

    def test_high_stress_multiplier(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        points = manager._calculate_growth_points(
            duration_minutes=30,
            mood_before=3,
            mood_after=3,
            phase="midday",
            had_yesterday=False,
            stress=5,
        )
        # base=30 + 0 + 0 + 5 = 35 * 1.0
        assert points == 35.0


# --- 成長段階テスト ---


class TestGrowthStage:
    def test_seed_stage(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        stage = manager._get_growth_stage(10)
        assert stage["name"] == "種"

    def test_sprout_stage(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        stage = manager._get_growth_stage(35)
        assert stage["name"] == "芽"

    def test_sapling_stage(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        stage = manager._get_growth_stage(65)
        assert stage["name"] == "若木"

    def test_tree_stage(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        stage = manager._get_growth_stage(90)
        assert stage["name"] == "樹木"

    def test_blossom_stage(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        stage = manager._get_growth_stage(100)
        assert stage["name"] == "開花"


# --- フェーズテスト ---


class TestPhase:
    def test_phase_definitions(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        assert "sunrise" in PHASES
        assert "midday" in PHASES
        assert "sunset" in PHASES
        assert "nightfall" in PHASES

    def test_current_phase_returns_valid(self, sanctuary_manager):
        manager, _ = sanctuary_manager
        phase = manager._get_current_phase()
        assert phase in PHASES


# --- 庭園管理テスト ---


class TestGardenManagement:
    @pytest.mark.asyncio
    async def test_ensure_garden_creates_new(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchrow.side_effect = [
            None,  # get_garden returns None
            {"user_id": 123, "vitality": 0, "harmony": 0, "season": "spring"},  # create_garden
        ]
        conn.execute.return_value = None

        garden = await manager.ensure_garden(123)
        assert garden["user_id"] == 123

    @pytest.mark.asyncio
    async def test_ensure_garden_returns_existing(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchrow.return_value = {
            "user_id": 123,
            "vitality": 50,
            "harmony": 30,
            "season": "summer",
        }

        garden = await manager.ensure_garden(123)
        assert garden["vitality"] == 50

    @pytest.mark.asyncio
    async def test_plant_seed_valid(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchval.return_value = 0  # count_plants
        garden_row = {
            "user_id": 123,
            "vitality": 0,
            "harmony": 0,
            "season": "spring",
        }
        plant_row = {
            "id": 1,
            "user_id": 123,
            "plant_type": "sakura",
            "name": "桜",
            "growth": 0,
            "health": 100,
        }
        conn.fetchrow.side_effect = [garden_row, plant_row]

        result = await manager.plant_seed(123, "sakura", "桜")
        assert result is not None
        assert result["plant_type"] == "sakura"

    @pytest.mark.asyncio
    async def test_plant_seed_invalid_type(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        result = await manager.plant_seed(123, "invalid_plant")
        assert result is None

    @pytest.mark.asyncio
    async def test_plant_seed_max_reached(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchval.return_value = MAX_PLANTS  # count_plants at max

        result = await manager.plant_seed(123, "sakura")
        assert result is None

    @pytest.mark.asyncio
    async def test_tend_garden(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetch.return_value = [
            {"id": 1, "name": "桜", "plant_type": "sakura", "growth": 50, "health": 80},
            {"id": 2, "name": "松", "plant_type": "pine", "growth": 30, "health": 60},
        ]
        conn.execute.return_value = None

        result = await manager.tend_garden(123)
        assert result["count"] == 2
        assert len(result["tended"]) == 2
        assert result["tended"][0]["health_after"] == 90
        assert result["tended"][1]["health_after"] == 70


# --- セッション管理テスト ---


class TestSessionManagement:
    @pytest.mark.asyncio
    async def test_start_session_success(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        garden_row = {
            "user_id": 123,
            "vitality": 0,
            "harmony": 0,
            "season": "spring",
        }
        session_row = {
            "id": 1,
            "user_id": 123,
            "phase": "midday",
            "mood_before": 3,
            "energy_before": 3,
        }
        conn.fetchrow.side_effect = [None, garden_row, session_row]

        session = await manager.start_session(123, 3, 3)
        assert session is not None
        assert session["phase"] == "midday"

    @pytest.mark.asyncio
    async def test_start_session_already_active(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchrow.return_value = {
            "id": 1,
            "user_id": 123,
            "phase": "midday",
            "completed": False,
        }

        result = await manager.start_session(123, 3, 3)
        assert result is None

    @pytest.mark.asyncio
    async def test_complete_session_success(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchrow.side_effect = [
            # get_active_session
            {"id": 1, "user_id": 123, "phase": "midday", "mood_before": 3, "energy_before": 3},
        ]
        conn.fetchval.side_effect = [
            0,  # had_session_yesterday
        ]
        conn.execute.return_value = None
        conn.fetch.return_value = [
            {"id": 1, "name": "桜", "plant_type": "sakura", "growth": 40, "health": 80},
        ]

        result = await manager.complete_session(123, 4, 4, 30, "良かった")
        assert result is not None
        assert result["growth_points"] > 0
        assert len(result["grown_plants"]) == 1

    @pytest.mark.asyncio
    async def test_complete_session_no_active(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchrow.return_value = None  # no active session

        result = await manager.complete_session(123, 4, 4, 30)
        assert result is None


# --- 外部連携テスト ---


class TestExternalIntegration:
    @pytest.mark.asyncio
    async def test_award_growth_from_study(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchrow.return_value = {
            "user_id": 123,
            "vitality": 50,
            "harmony": 30,
            "season": "spring",
        }
        conn.fetchval.return_value = 0  # had_session_yesterday
        conn.fetch.return_value = [
            {"id": 1, "name": "桜", "plant_type": "sakura", "growth": 30, "health": 80},
        ]
        conn.execute.return_value = None

        growth = await manager.award_growth_from_study(123, 30)
        assert growth > 0

    @pytest.mark.asyncio
    async def test_award_growth_no_garden(self, sanctuary_manager):
        manager, conn = sanctuary_manager
        conn.fetchrow.return_value = None  # no garden

        growth = await manager.award_growth_from_study(123, 30)
        assert growth == 0.0


# --- 定数テスト ---


class TestConstants:
    def test_plant_types_defined(self):
        assert len(PLANT_TYPES) >= 8
        for _key, val in PLANT_TYPES.items():
            assert "name" in val
            assert "emoji" in val

    def test_growth_stages_coverage(self):
        """成長段階が0-100をカバーする"""
        assert GROWTH_STAGES[0]["min"] == 0
        assert GROWTH_STAGES[-1]["max"] == 100

    def test_phases_have_hours(self):
        for _key, phase in PHASES.items():
            assert "hours" in phase
            assert "bonus" in phase
            assert "name" in phase
