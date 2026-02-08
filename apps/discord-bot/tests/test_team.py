"""スタディチームのテスト"""

import pytest

from studybot.managers.team_manager import TeamManager


@pytest.fixture
def team_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = TeamManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_create_team(team_manager):
    """チーム作成テスト"""
    manager, conn = team_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.return_value = {
        "id": 1,
        "name": "数学チーム",
        "creator_id": 123,
        "guild_id": 456,
        "max_members": 10,
        "created_at": None,
    }
    conn.fetchval.return_value = 0  # count_user_teams

    result = await manager.create_team(
        creator_id=123,
        username="TestUser",
        guild_id=456,
        name="数学チーム",
    )

    assert "error" not in result
    assert result["team_id"] == 1
    assert result["name"] == "数学チーム"
    assert result["max_members"] == 10


@pytest.mark.asyncio
async def test_create_team_name_too_short(team_manager):
    """チーム名が短すぎる場合"""
    manager, conn = team_manager

    conn.execute.return_value = None  # ensure_user

    result = await manager.create_team(
        creator_id=123,
        username="TestUser",
        guild_id=456,
        name="A",
    )

    assert "error" in result
    assert "2文字以上" in result["error"]


@pytest.mark.asyncio
async def test_create_team_max_teams_exceeded(team_manager):
    """チーム作成上限テスト"""
    manager, conn = team_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchval.return_value = 3  # count_user_teams = already at max

    result = await manager.create_team(
        creator_id=123,
        username="TestUser",
        guild_id=456,
        name="4つ目のチーム",
    )

    assert "error" in result
    assert "3つまで" in result["error"]


@pytest.mark.asyncio
async def test_join_team(team_manager):
    """チーム参加テスト"""
    manager, conn = team_manager

    conn.execute.side_effect = [
        None,  # ensure_user
        None,  # join_team INSERT
    ]
    conn.fetchrow.side_effect = [
        # get_team
        {
            "id": 1,
            "name": "数学チーム",
            "creator_id": 111,
            "guild_id": 456,
            "max_members": 10,
            "member_count": 3,
            "created_at": None,
        },
        # get_member (not found = can join)
        None,
    ]

    result = await manager.join_team(
        team_id=1,
        user_id=123,
        username="TestUser",
    )

    assert "error" not in result
    assert result["name"] == "数学チーム"
    assert result["member_count"] == 4


@pytest.mark.asyncio
async def test_join_full_team(team_manager):
    """満員チームへの参加テスト"""
    manager, conn = team_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        # get_team (full)
        {
            "id": 1,
            "name": "満員チーム",
            "creator_id": 111,
            "guild_id": 456,
            "max_members": 3,
            "member_count": 3,
            "created_at": None,
        },
        # get_member (not found)
        None,
    ]

    result = await manager.join_team(
        team_id=1,
        user_id=999,
        username="NewUser",
    )

    assert "error" in result
    assert "満員" in result["error"]


@pytest.mark.asyncio
async def test_leave_team(team_manager):
    """チーム脱退テスト"""
    manager, conn = team_manager

    conn.fetchrow.side_effect = [
        # get_team
        {
            "id": 1,
            "name": "数学チーム",
            "creator_id": 111,
            "guild_id": 456,
            "max_members": 10,
            "member_count": 5,
            "created_at": None,
        },
        # get_member (exists)
        {
            "team_id": 1,
            "user_id": 123,
            "username": "TestUser",
            "joined_at": None,
        },
    ]
    conn.execute.return_value = "DELETE 1"

    result = await manager.leave_team(
        team_id=1,
        user_id=123,
    )

    assert "error" not in result
    assert result["name"] == "数学チーム"


@pytest.mark.asyncio
async def test_leave_team_not_member(team_manager):
    """参加していないチームからの脱退テスト"""
    manager, conn = team_manager

    conn.fetchrow.side_effect = [
        # get_team
        {
            "id": 1,
            "name": "数学チーム",
            "creator_id": 111,
            "guild_id": 456,
            "max_members": 10,
            "member_count": 5,
            "created_at": None,
        },
        # get_member (not found)
        None,
    ]

    result = await manager.leave_team(
        team_id=1,
        user_id=999,
    )

    assert "error" in result
    assert "参加していません" in result["error"]


@pytest.mark.asyncio
async def test_get_team_stats(team_manager):
    """チーム統計テスト"""
    manager, conn = team_manager

    conn.fetchrow.side_effect = [
        # get_team
        {
            "id": 1,
            "name": "数学チーム",
            "creator_id": 111,
            "guild_id": 456,
            "max_members": 10,
            "member_count": 3,
            "created_at": None,
        },
        # get_team_stats
        {
            "total_minutes": 600,
            "total_sessions": 20,
            "member_count": 3,
        },
        # get_team_weekly_stats
        {
            "weekly_minutes": 120,
            "weekly_sessions": 8,
            "member_count": 3,
        },
    ]

    result = await manager.get_team_stats(team_id=1)

    assert result is not None
    assert result["team"]["name"] == "数学チーム"
    assert result["stats"]["total_minutes"] == 600
    assert result["stats"]["avg_minutes_per_member"] == 200
    assert result["weekly"]["weekly_minutes"] == 120


@pytest.mark.asyncio
async def test_get_team_stats_not_found(team_manager):
    """存在しないチームの統計テスト"""
    manager, conn = team_manager

    conn.fetchrow.return_value = None  # get_team returns None

    result = await manager.get_team_stats(team_id=999)

    assert result is None


@pytest.mark.asyncio
async def test_list_guild_teams(team_manager):
    """サーバーチーム一覧テスト"""
    manager, conn = team_manager

    conn.fetch.return_value = [
        {
            "id": 1,
            "name": "数学チーム",
            "creator_id": 111,
            "guild_id": 456,
            "max_members": 10,
            "member_count": 5,
            "created_at": None,
        },
        {
            "id": 2,
            "name": "英語チーム",
            "creator_id": 222,
            "guild_id": 456,
            "max_members": 8,
            "member_count": 3,
            "created_at": None,
        },
    ]

    teams = await manager.list_guild_teams(guild_id=456)
    assert len(teams) == 2
    assert teams[0]["name"] == "数学チーム"
    assert teams[1]["member_count"] == 3


@pytest.mark.asyncio
async def test_join_team_already_member(team_manager):
    """既にメンバーのチームへの参加テスト"""
    manager, conn = team_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        # get_team
        {
            "id": 1,
            "name": "数学チーム",
            "creator_id": 111,
            "guild_id": 456,
            "max_members": 10,
            "member_count": 5,
            "created_at": None,
        },
        # get_member (already exists)
        {
            "team_id": 1,
            "user_id": 123,
            "username": "TestUser",
            "joined_at": None,
        },
    ]

    result = await manager.join_team(
        team_id=1,
        user_id=123,
        username="TestUser",
    )

    assert "error" in result
    assert "既に" in result["error"]


@pytest.mark.asyncio
async def test_get_team_members(team_manager):
    """チームメンバー取得テスト"""
    manager, conn = team_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "name": "数学チーム",
        "creator_id": 111,
        "guild_id": 456,
        "max_members": 10,
        "member_count": 2,
        "created_at": None,
    }
    conn.fetch.return_value = [
        {
            "user_id": 111,
            "username": "Leader",
            "joined_at": None,
        },
        {
            "user_id": 222,
            "username": "Member1",
            "joined_at": None,
        },
    ]

    result = await manager.get_team_members(team_id=1)

    assert "error" not in result
    assert result["team"]["name"] == "数学チーム"
    assert len(result["members"]) == 2
    assert result["members"][0]["username"] == "Leader"
