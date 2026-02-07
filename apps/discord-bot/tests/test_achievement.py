"""実績システムのテスト"""

import pytest

from studybot.managers.achievement_manager import AchievementManager


@pytest.fixture
def achievement_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = AchievementManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_check_and_update_unlock(achievement_manager):
    """実績アンロックテスト"""
    manager, conn = achievement_manager

    # get_achievement_by_key
    conn.fetchrow.side_effect = [
        {
            "id": 1,
            "key": "first_study",
            "name": "初学者",
            "description": "初めて学習を記録した",
            "emoji": "📖",
            "category": "study",
            "target_value": 1,
            "reward_coins": 50,
        },
        # get_user_progress -> None (no progress yet)
        None,
    ]
    conn.execute.return_value = None  # update_progress, unlock_achievement

    result = await manager.check_and_update(123, "first_study", 1)
    assert result is not None
    assert result["unlocked"] is True
    assert result["achievement"]["name"] == "初学者"
    assert result["reward_coins"] == 50


@pytest.mark.asyncio
async def test_check_and_update_no_unlock(achievement_manager):
    """目標未達でアンロックされないテスト"""
    manager, conn = achievement_manager

    conn.fetchrow.side_effect = [
        # get_achievement_by_key
        {
            "id": 2,
            "key": "study_100h",
            "name": "100時間学習者",
            "description": "累計100時間学習した",
            "emoji": "📚",
            "category": "study",
            "target_value": 6000,
            "reward_coins": 500,
        },
        # get_user_progress -> existing progress
        {
            "id": 1,
            "user_id": 123,
            "achievement_id": 2,
            "progress": 100,
            "unlocked": False,
            "unlocked_at": None,
            "key": "study_100h",
            "name": "100時間学習者",
            "target_value": 6000,
            "reward_coins": 500,
            "emoji": "📚",
        },
    ]
    conn.execute.return_value = None  # update_progress

    result = await manager.check_and_update(123, "study_100h", 200)
    assert result is None  # not unlocked yet


@pytest.mark.asyncio
async def test_check_and_update_already_unlocked(achievement_manager):
    """既にアンロック済みの実績は再度処理されない"""
    manager, conn = achievement_manager

    conn.fetchrow.side_effect = [
        # get_achievement_by_key
        {
            "id": 1,
            "key": "first_study",
            "name": "初学者",
            "description": "初めて学習を記録した",
            "emoji": "📖",
            "category": "study",
            "target_value": 1,
            "reward_coins": 50,
        },
        # get_user_progress -> already unlocked
        {
            "id": 1,
            "user_id": 123,
            "achievement_id": 1,
            "progress": 1,
            "unlocked": True,
            "unlocked_at": "2025-01-01",
            "key": "first_study",
            "name": "初学者",
            "target_value": 1,
            "reward_coins": 50,
            "emoji": "📖",
        },
    ]

    result = await manager.check_and_update(123, "first_study", 1)
    assert result is None  # already unlocked, no action


@pytest.mark.asyncio
async def test_check_and_update_unknown_key(achievement_manager):
    """存在しない実績キー"""
    manager, conn = achievement_manager

    conn.fetchrow.return_value = None  # get_achievement_by_key returns None

    result = await manager.check_and_update(123, "nonexistent_key", 1)
    assert result is None


@pytest.mark.asyncio
async def test_get_all_with_progress(achievement_manager):
    """全実績取得テスト"""
    manager, conn = achievement_manager

    conn.fetch.return_value = [
        {
            "id": 1,
            "key": "first_study",
            "name": "初学者",
            "description": "初めて学習を記録した",
            "emoji": "📖",
            "category": "study",
            "target_value": 1,
            "reward_coins": 50,
            "progress": 1,
            "unlocked": True,
            "unlocked_at": None,
        },
        {
            "id": 2,
            "key": "study_100h",
            "name": "100時間学習者",
            "description": "累計100時間学習した",
            "emoji": "📚",
            "category": "study",
            "target_value": 6000,
            "reward_coins": 500,
            "progress": 120,
            "unlocked": False,
            "unlocked_at": None,
        },
    ]

    result = await manager.get_all_with_progress(123)
    assert len(result) == 2
    assert result[0]["unlocked"] is True
    assert result[1]["progress"] == 120


@pytest.mark.asyncio
async def test_get_user_unlocked(achievement_manager):
    """アンロック済み実績のみ取得"""
    manager, conn = achievement_manager

    conn.fetch.return_value = [
        {
            "id": 1,
            "key": "first_study",
            "name": "初学者",
            "description": "初めて学習を記録した",
            "emoji": "📖",
            "category": "study",
            "target_value": 1,
            "reward_coins": 50,
            "progress": 1,
            "unlocked": True,
            "unlocked_at": None,
        },
        {
            "id": 2,
            "key": "study_100h",
            "name": "100時間学習者",
            "description": "累計100時間学習した",
            "emoji": "📚",
            "category": "study",
            "target_value": 6000,
            "reward_coins": 500,
            "progress": 120,
            "unlocked": False,
            "unlocked_at": None,
        },
    ]

    result = await manager.get_user_unlocked(123)
    assert len(result) == 1
    assert result[0]["key"] == "first_study"


@pytest.mark.asyncio
async def test_check_and_update_progress_increases(achievement_manager):
    """進捗が既存値より大きい場合のみ更新される"""
    manager, conn = achievement_manager

    conn.fetchrow.side_effect = [
        # get_achievement_by_key
        {
            "id": 7,
            "key": "raid_master",
            "name": "レイドマスター",
            "description": "10回スタディレイドを完了した",
            "emoji": "🛡️",
            "category": "raid",
            "target_value": 10,
            "reward_coins": 300,
        },
        # get_user_progress -> existing progress = 8
        {
            "id": 5,
            "user_id": 123,
            "achievement_id": 7,
            "progress": 8,
            "unlocked": False,
            "unlocked_at": None,
            "key": "raid_master",
            "name": "レイドマスター",
            "target_value": 10,
            "reward_coins": 300,
            "emoji": "🛡️",
        },
    ]
    conn.execute.return_value = None

    # new_value=9 > current progress=8, but < target=10
    result = await manager.check_and_update(123, "raid_master", 9)
    assert result is None  # not yet unlocked

    # Verify update_progress was called with 9
    conn.execute.assert_called()
