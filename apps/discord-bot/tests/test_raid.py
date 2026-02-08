"""スタディレイドのテスト"""

import asyncpg
import pytest

from studybot.config.constants import RAID_DEFAULTS
from studybot.managers.raid_manager import RaidManager


@pytest.fixture
def raid_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = RaidManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_create_raid(raid_manager):
    """レイド作成テスト"""
    manager, conn = raid_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        # create_raid -> INSERT RETURNING
        {
            "id": 1,
            "creator_id": 123,
            "guild_id": 456,
            "channel_id": 789,
            "topic": "数学",
            "duration_minutes": 30,
            "max_participants": 10,
            "state": "recruiting",
            "started_at": None,
            "ended_at": None,
            "created_at": None,
        },
    ]

    result = await manager.create_raid(
        creator_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
        topic="数学",
        duration=30,
    )

    assert result["id"] == 1
    assert result["topic"] == "数学"
    assert result["state"] == "recruiting"
    assert "error" not in result


@pytest.mark.asyncio
async def test_create_raid_duration_too_short(raid_manager):
    """レイド作成 - 時間が短すぎる"""
    manager, conn = raid_manager

    conn.execute.return_value = None  # ensure_user

    result = await manager.create_raid(
        creator_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
        topic="数学",
        duration=5,  # min is 15
    )

    assert "error" in result


@pytest.mark.asyncio
async def test_create_raid_duration_too_long(raid_manager):
    """レイド作成 - 時間が長すぎる"""
    manager, conn = raid_manager

    conn.execute.return_value = None  # ensure_user

    result = await manager.create_raid(
        creator_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
        topic="数学",
        duration=300,  # max is 180
    )

    assert "error" in result


@pytest.mark.asyncio
async def test_join_raid(raid_manager):
    """レイド参加テスト"""
    manager, conn = raid_manager

    conn.execute.side_effect = [
        None,  # ensure_user
        None,  # add_participant
    ]
    conn.fetchrow.return_value = {
        "id": 1,
        "creator_id": 111,
        "guild_id": 456,
        "channel_id": 789,
        "topic": "数学",
        "duration_minutes": 30,
        "max_participants": 10,
        "state": "recruiting",
        "started_at": None,
        "ended_at": None,
        "created_at": None,
    }
    conn.fetchval.side_effect = [
        5,  # get_participant_count (before max check)
        6,  # get_participant_count (after join)
    ]

    result = await manager.join_raid(1, 123, "TestUser")
    assert "error" not in result
    assert result["participant_count"] == 6


@pytest.mark.asyncio
async def test_join_raid_full(raid_manager):
    """満員レイドへの参加テスト"""
    manager, conn = raid_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.return_value = {
        "id": 1,
        "creator_id": 111,
        "guild_id": 456,
        "channel_id": 789,
        "topic": "数学",
        "duration_minutes": 30,
        "max_participants": 5,
        "state": "recruiting",
        "started_at": None,
        "ended_at": None,
        "created_at": None,
    }
    conn.fetchval.return_value = 5  # already full

    result = await manager.join_raid(1, 123, "TestUser")
    assert "error" in result
    assert "上限" in result["error"]


@pytest.mark.asyncio
async def test_join_raid_already_joined(raid_manager):
    """既に参加済みのレイドへの参加テスト"""
    manager, conn = raid_manager

    conn.execute.side_effect = [
        None,  # ensure_user
        asyncpg.UniqueViolationError("UNIQUE constraint"),  # add_participant fails
    ]
    conn.fetchrow.return_value = {
        "id": 1,
        "creator_id": 111,
        "guild_id": 456,
        "channel_id": 789,
        "topic": "数学",
        "duration_minutes": 30,
        "max_participants": 10,
        "state": "recruiting",
        "started_at": None,
        "ended_at": None,
        "created_at": None,
    }
    conn.fetchval.return_value = 3  # participant count

    result = await manager.join_raid(1, 123, "TestUser")
    assert "error" in result
    assert "既に参加" in result["error"]


@pytest.mark.asyncio
async def test_leave_raid(raid_manager):
    """レイド離脱テスト"""
    manager, conn = raid_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "creator_id": 111,
        "guild_id": 456,
        "channel_id": 789,
        "topic": "数学",
        "duration_minutes": 30,
        "max_participants": 10,
        "state": "recruiting",
        "started_at": None,
        "ended_at": None,
        "created_at": None,
    }
    conn.execute.return_value = "DELETE 1"

    result = await manager.leave_raid(1, 123)
    assert result.get("success") is True


@pytest.mark.asyncio
async def test_leave_raid_creator_denied(raid_manager):
    """レイド作成者の離脱拒否テスト"""
    manager, conn = raid_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "creator_id": 123,  # same as user trying to leave
        "guild_id": 456,
        "channel_id": 789,
        "topic": "数学",
        "duration_minutes": 30,
        "max_participants": 10,
        "state": "recruiting",
        "started_at": None,
        "ended_at": None,
        "created_at": None,
    }

    result = await manager.leave_raid(1, 123)
    assert "error" in result
    assert "作成者" in result["error"]


@pytest.mark.asyncio
async def test_start_raid(raid_manager):
    """レイド開始テスト"""
    manager, conn = raid_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "creator_id": 123,
        "guild_id": 456,
        "channel_id": 789,
        "topic": "数学",
        "duration_minutes": 30,
        "max_participants": 10,
        "state": "recruiting",
        "started_at": None,
        "ended_at": None,
        "created_at": None,
    }
    conn.execute.return_value = None
    conn.fetch.return_value = [
        {"user_id": 123, "username": "User1", "raid_id": 1, "joined_at": None, "completed": False},
        {"user_id": 456, "username": "User2", "raid_id": 1, "joined_at": None, "completed": False},
    ]

    result = await manager.start_raid(1)
    assert "error" not in result
    assert len(result["participants"]) == 2
    assert 1 in manager.active_raids


@pytest.mark.asyncio
async def test_complete_raid(raid_manager):
    """レイド完了テスト"""
    manager, conn = raid_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "creator_id": 123,
        "guild_id": 456,
        "channel_id": 789,
        "topic": "数学",
        "duration_minutes": 30,
        "max_participants": 10,
        "state": "active",
        "started_at": None,
        "ended_at": None,
        "created_at": None,
    }
    conn.execute.return_value = None
    conn.fetch.return_value = [
        {"user_id": 123, "username": "User1", "raid_id": 1, "joined_at": None, "completed": False},
        {"user_id": 456, "username": "User2", "raid_id": 1, "joined_at": None, "completed": False},
    ]

    # メモリにタイマーを設置
    from datetime import UTC, datetime

    manager.active_raids[1] = {
        "raid_id": 1,
        "started_at": datetime.now(UTC),
        "duration_minutes": 30,
        "channel_id": 789,
        "guild_id": 456,
        "topic": "数学",
        "creator_id": 123,
    }

    result = await manager.complete_raid(1)
    assert "error" not in result
    assert len(result["participants"]) == 2
    assert 1 not in manager.active_raids  # タイマー削除確認


@pytest.mark.asyncio
async def test_xp_multiplier():
    """XP倍率の確認"""
    base_xp = 10
    multiplied = int(base_xp * RAID_DEFAULTS["xp_multiplier"])
    assert multiplied == 15  # 10 * 1.5 = 15


@pytest.mark.asyncio
async def test_get_active_raids(raid_manager):
    """アクティブレイド取得テスト"""
    manager, conn = raid_manager

    conn.fetch.return_value = [
        {
            "id": 1,
            "creator_id": 123,
            "guild_id": 456,
            "channel_id": 789,
            "topic": "数学",
            "duration_minutes": 30,
            "max_participants": 10,
            "state": "recruiting",
            "started_at": None,
            "ended_at": None,
            "created_at": None,
            "creator_name": "TestUser",
            "participant_count": 3,
        }
    ]

    raids = await manager.get_active_raids(456)
    assert len(raids) == 1
    assert raids[0]["participant_count"] == 3
