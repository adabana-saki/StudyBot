"""チームバトルのテスト"""

from datetime import date, timedelta

import pytest

from studybot.managers.battle_manager import BattleManager
from studybot.repositories.battle_repository import BattleRepository


@pytest.fixture
def battle_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = BattleManager(pool)
    return manager, conn


@pytest.fixture
def battle_repo(mock_db_pool):
    pool, conn = mock_db_pool
    repo = BattleRepository(pool)
    return repo, conn


@pytest.mark.asyncio
async def test_create_battle(battle_manager):
    """バトル作成テスト"""
    manager, conn = battle_manager
    today = date.today()

    conn.fetchrow.side_effect = [
        # team_a
        {"id": 1, "name": "Alpha", "guild_id": 100, "member_count": 3},
        # team_b
        {"id": 2, "name": "Beta", "guild_id": 100, "member_count": 4},
        # create_battle
        {
            "id": 1,
            "guild_id": 100,
            "team_a_id": 1,
            "team_b_id": 2,
            "goal_type": "study_minutes",
            "duration_days": 7,
            "start_date": today,
            "end_date": today + timedelta(days=7),
            "team_a_score": 0,
            "team_b_score": 0,
            "winner_team_id": None,
            "status": "pending",
            "xp_multiplier": 2.0,
            "created_at": None,
        },
    ]

    result = await manager.create_battle(100, 1, 2, "study_minutes", 7)
    assert result["battle_id"] == 1
    assert result["team_a_name"] == "Alpha"
    assert result["team_b_name"] == "Beta"


@pytest.mark.asyncio
async def test_create_battle_same_team(battle_manager):
    """同チームバトル作成拒否"""
    manager, conn = battle_manager
    result = await manager.create_battle(100, 1, 1, "study_minutes", 7)
    assert "error" in result


@pytest.mark.asyncio
async def test_create_battle_invalid_goal(battle_manager):
    """無効なgoal_type"""
    manager, conn = battle_manager
    result = await manager.create_battle(100, 1, 2, "invalid", 7)
    assert "error" in result


@pytest.mark.asyncio
async def test_accept_battle(battle_manager):
    """バトル承認テスト"""
    manager, conn = battle_manager
    conn.fetchrow.side_effect = [
        # get_battle
        {"id": 1, "status": "pending", "team_a_id": 1, "team_b_id": 2},
        # get_team
        {"id": 2, "name": "Beta", "guild_id": 100, "member_count": 3},
        # get_member
        {"team_id": 2, "user_id": 200, "username": "User2", "joined_at": None},
    ]
    conn.execute.return_value = None

    result = await manager.accept_battle(1, 200)
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_add_contribution(battle_manager):
    """貢献記録テスト"""
    manager, conn = battle_manager
    date.today()

    conn.fetch.return_value = [
        {
            "id": 1,
            "goal_type": "study_minutes",
            "user_team_id": 1,
            "team_a_id": 1,
            "team_b_id": 2,
            "team_a_score": 100,
            "team_b_score": 50,
            "status": "active",
        }
    ]
    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        # update_battle_score: SELECT * FROM team_battles
        {
            "id": 1,
            "team_a_id": 1,
            "team_b_id": 2,
            "team_a_score": 100,
            "team_b_score": 50,
        },
        # update_battle_score: UPDATE RETURNING *
        {
            "id": 1,
            "team_a_score": 130,
            "team_b_score": 50,
        },
    ]

    await manager.add_contribution(123, "study_minutes", 30, "discord")
    conn.execute.assert_called()


@pytest.mark.asyncio
async def test_check_battle_completion(battle_manager):
    """バトル完了チェック"""
    manager, conn = battle_manager
    yesterday = date.today() - timedelta(days=1)

    conn.fetch.return_value = [
        {
            "id": 1,
            "team_a_id": 1,
            "team_b_id": 2,
            "team_a_score": 500,
            "team_b_score": 300,
            "status": "active",
            "end_date": yesterday,
        }
    ]
    conn.execute.return_value = None

    results = await manager.check_battle_completion()
    assert len(results) == 1
    assert results[0]["winner_team_id"] == 1


@pytest.mark.asyncio
async def test_check_battle_completion_draw(battle_manager):
    """引き分けテスト"""
    manager, conn = battle_manager
    yesterday = date.today() - timedelta(days=1)

    conn.fetch.return_value = [
        {
            "id": 2,
            "team_a_id": 1,
            "team_b_id": 2,
            "team_a_score": 300,
            "team_b_score": 300,
            "status": "active",
            "end_date": yesterday,
        }
    ]
    conn.execute.return_value = None

    results = await manager.check_battle_completion()
    assert results[0]["winner_team_id"] is None
