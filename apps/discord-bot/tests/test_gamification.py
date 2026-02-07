"""ゲーミフィケーションのテスト"""

from datetime import date, timedelta

import pytest

from studybot.config.constants import LEVEL_FORMULA, XP_REWARDS
from studybot.managers.gamification_manager import GamificationManager


@pytest.fixture
def gamification_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = GamificationManager(pool)
    return manager, conn


def test_level_formula():
    """レベル計算式テスト: level² × 100"""
    assert LEVEL_FORMULA(1) == 100
    assert LEVEL_FORMULA(2) == 400
    assert LEVEL_FORMULA(5) == 2500
    assert LEVEL_FORMULA(10) == 10000


def test_calculate_level():
    """累計XPからレベル計算"""
    manager = GamificationManager.__new__(GamificationManager)

    # 0 XP = Level 1
    assert manager._calculate_level(0) == 1

    # 400 XP = Level 2 (need 400 for level 2)
    assert manager._calculate_level(400) == 2

    # 399 XP = Level 1
    assert manager._calculate_level(399) == 1

    # 1300 XP = Level 3 (400 + 900 = 1300)
    assert manager._calculate_level(1300) == 3


@pytest.mark.asyncio
async def test_add_xp(gamification_manager):
    """XP付与テスト"""
    manager, conn = gamification_manager

    conn.execute.return_value = None  # xp_transaction insert
    conn.fetchrow.side_effect = [
        # add_xp returns updated user_levels row
        {
            "user_id": 123,
            "xp": 410,
            "level": 1,
            "streak_days": 0,
            "last_study_date": None,
            "updated_at": None,
        },
        # get_milestone returns None (no milestone at level 2)
        None,
    ]

    result = await manager.add_xp(123, 10, "テスト")
    assert result["xp_gained"] == 10
    assert result["total_xp"] == 410


@pytest.mark.asyncio
async def test_check_streak_new_day(gamification_manager):
    """連続学習チェック - 新しい日"""
    manager, conn = gamification_manager

    yesterday = date.today() - timedelta(days=1)
    conn.fetchrow.return_value = {
        "user_id": 123,
        "xp": 100,
        "level": 1,
        "streak_days": 3,
        "last_study_date": yesterday,
        "updated_at": None,
    }
    conn.execute.return_value = None

    result = await manager.check_streak(123)
    assert result["streak"] == 4
    assert result["bonus"] is False


@pytest.mark.asyncio
async def test_check_streak_reset(gamification_manager):
    """連続学習チェック - リセット"""
    manager, conn = gamification_manager

    two_days_ago = date.today() - timedelta(days=2)
    conn.fetchrow.return_value = {
        "user_id": 123,
        "xp": 100,
        "level": 1,
        "streak_days": 5,
        "last_study_date": two_days_ago,
        "updated_at": None,
    }
    conn.execute.return_value = None

    result = await manager.check_streak(123)
    assert result["streak"] == 1  # reset to 1


@pytest.mark.asyncio
async def test_check_streak_7day_bonus(gamification_manager):
    """7日連続ボーナス"""
    manager, conn = gamification_manager

    yesterday = date.today() - timedelta(days=1)
    conn.fetchrow.side_effect = [
        # get_user_level
        {
            "user_id": 123,
            "xp": 100,
            "level": 1,
            "streak_days": 6,
            "last_study_date": yesterday,
            "updated_at": None,
        },
        # add_xp (for streak bonus)
        {
            "user_id": 123,
            "xp": 150,
            "level": 1,
            "streak_days": 7,
            "last_study_date": None,
            "updated_at": None,
        },
    ]
    conn.execute.return_value = None

    result = await manager.check_streak(123)
    assert result["streak"] == 7
    assert result["bonus"] is True


def test_xp_rewards_defined():
    """XP報酬が定義されていること"""
    assert "pomodoro_complete" in XP_REWARDS
    assert "task_complete_high" in XP_REWARDS
    assert "study_log" in XP_REWARDS
    assert "streak_bonus" in XP_REWARDS
    assert XP_REWARDS["pomodoro_complete"] == 10
    assert XP_REWARDS["streak_bonus"] == 50
