"""スタディルームのテスト"""

from datetime import UTC, datetime

import pytest

from studybot.managers.room_manager import RoomManager
from studybot.repositories.room_repository import RoomRepository


@pytest.fixture
def room_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = RoomManager(pool)
    return manager, conn


@pytest.fixture
def room_repo(mock_db_pool):
    pool, conn = mock_db_pool
    repo = RoomRepository(pool)
    return repo, conn


@pytest.mark.asyncio
async def test_create_room(room_manager):
    """ルーム作成テスト"""
    manager, conn = room_manager
    conn.fetchrow.return_value = {
        "id": 1,
        "guild_id": 100,
        "name": "数学部屋",
        "theme": "math",
        "vc_channel_id": None,
        "collective_goal_minutes": 120,
        "collective_progress_minutes": 0,
        "max_occupants": 20,
        "description": "",
        "ambient_sound": "none",
        "is_permanent": False,
        "state": "active",
        "created_by": 123,
        "created_at": None,
    }

    result = await manager.create_room(100, "数学部屋", "math", goal_minutes=120, created_by=123)
    assert result["id"] == 1
    assert result["name"] == "数学部屋"


@pytest.mark.asyncio
async def test_create_room_invalid_theme(room_manager):
    """無効テーマテスト"""
    manager, conn = room_manager
    result = await manager.create_room(100, "部屋", "invalid_theme")
    assert "error" in result


@pytest.mark.asyncio
async def test_join_room(room_manager):
    """ルーム参加テスト"""
    manager, conn = room_manager

    conn.fetchrow.side_effect = [
        # get_room
        {
            "id": 1,
            "guild_id": 100,
            "name": "部屋",
            "member_count": 5,
            "max_occupants": 20,
        },
        # get_user_room (no existing room)
        None,
    ]
    conn.execute.return_value = None

    result = await manager.join_room(1, 123, "discord", "数学")
    assert result["status"] == "joined"


@pytest.mark.asyncio
async def test_join_room_full(room_manager):
    """満室テスト"""
    manager, conn = room_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "guild_id": 100,
        "name": "部屋",
        "member_count": 20,
        "max_occupants": 20,
    }

    result = await manager.join_room(1, 123, "discord")
    assert "error" in result
    assert "満員" in result["error"]


@pytest.mark.asyncio
async def test_leave_room(room_manager):
    """ルーム退出テスト"""
    manager, conn = room_manager
    now = datetime.now(UTC)

    conn.fetchrow.side_effect = [
        # leave_room -> member
        {
            "room_id": 1,
            "user_id": 123,
            "platform": "discord",
            "topic": "数学",
            "joined_at": now,
        },
        # update_collective_progress
        {"collective_goal_minutes": 120, "collective_progress_minutes": 60},
    ]
    conn.execute.return_value = None

    result = await manager.leave_room(1, 123)
    assert result["status"] == "left"


@pytest.mark.asyncio
async def test_leave_room_not_member(room_manager):
    """非参加者退出テスト"""
    manager, conn = room_manager
    conn.fetchrow.return_value = None

    result = await manager.leave_room(1, 123)
    assert "error" in result


@pytest.mark.asyncio
async def test_get_campus(room_manager):
    """キャンパス取得テスト"""
    manager, conn = room_manager
    conn.fetch.return_value = [
        {"id": 1, "guild_id": 100, "name": "数学", "member_count": 3},
        {"id": 2, "guild_id": 100, "name": "英語", "member_count": 5},
    ]

    rooms = await manager.get_campus(100)
    assert len(rooms) == 2
