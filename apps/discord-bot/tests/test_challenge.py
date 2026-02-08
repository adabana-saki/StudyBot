"""コホートチャレンジのテスト"""

from datetime import date, timedelta

import pytest

from studybot.managers.challenge_manager import ChallengeManager


@pytest.fixture
def challenge_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = ChallengeManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_create_challenge(challenge_manager):
    """チャレンジ作成テスト"""
    manager, conn = challenge_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchval.return_value = 1  # INSERT RETURNING id

    result = await manager.create_challenge(
        creator_id=123,
        username="TestUser",
        guild_id=456,
        name="7日間読書チャレンジ",
        duration_days=7,
        goal_type="study_minutes",
        goal_target=420,
    )

    assert "error" not in result
    assert result["challenge_id"] == 1
    assert result["name"] == "7日間読書チャレンジ"
    assert result["duration_days"] == 7
    assert result["goal_target"] == 420


@pytest.mark.asyncio
async def test_create_challenge_duration_too_short(challenge_manager):
    """チャレンジ作成 - 期間が短すぎる"""
    manager, conn = challenge_manager

    conn.execute.return_value = None  # ensure_user

    result = await manager.create_challenge(
        creator_id=123,
        username="TestUser",
        guild_id=456,
        name="短すぎチャレンジ",
        duration_days=2,  # min is 3
        goal_type="study_minutes",
        goal_target=100,
    )

    assert "error" in result
    assert "3〜90日" in result["error"]


@pytest.mark.asyncio
async def test_create_challenge_duration_too_long(challenge_manager):
    """チャレンジ作成 - 期間が長すぎる"""
    manager, conn = challenge_manager

    conn.execute.return_value = None  # ensure_user

    result = await manager.create_challenge(
        creator_id=123,
        username="TestUser",
        guild_id=456,
        name="長すぎチャレンジ",
        duration_days=100,  # max is 90
        goal_type="study_minutes",
        goal_target=100,
    )

    assert "error" in result
    assert "3〜90日" in result["error"]


@pytest.mark.asyncio
async def test_join_challenge(challenge_manager):
    """チャレンジ参加テスト"""
    manager, conn = challenge_manager

    conn.execute.side_effect = [
        None,  # ensure_user
        None,  # join_challenge INSERT
    ]
    conn.fetchrow.side_effect = [
        # get_challenge
        {
            "id": 1,
            "creator_id": 111,
            "guild_id": 456,
            "name": "テストチャレンジ",
            "description": "",
            "goal_type": "study_minutes",
            "goal_target": 600,
            "duration_days": 14,
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=14),
            "status": "active",
            "participant_count": 3,
            "creator_name": "Creator",
            "channel_id": None,
            "xp_multiplier": 1.5,
            "created_at": None,
        },
        # get_participant (not found = can join)
        None,
    ]

    result = await manager.join_challenge(
        challenge_id=1,
        user_id=123,
        username="TestUser",
    )

    assert "error" not in result
    assert result["name"] == "テストチャレンジ"
    assert result["participant_count"] == 4


@pytest.mark.asyncio
async def test_join_challenge_already_joined(challenge_manager):
    """既に参加済みのチャレンジへの参加テスト"""
    manager, conn = challenge_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        # get_challenge
        {
            "id": 1,
            "creator_id": 111,
            "guild_id": 456,
            "name": "テストチャレンジ",
            "description": "",
            "goal_type": "study_minutes",
            "goal_target": 600,
            "duration_days": 14,
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=14),
            "status": "active",
            "participant_count": 3,
            "creator_name": "Creator",
            "channel_id": None,
            "xp_multiplier": 1.5,
            "created_at": None,
        },
        # get_participant (already exists)
        {
            "challenge_id": 1,
            "user_id": 123,
            "progress": 100,
            "checkins": 2,
            "completed": False,
        },
    ]

    result = await manager.join_challenge(
        challenge_id=1,
        user_id=123,
        username="TestUser",
    )

    assert "error" in result
    assert "既に参加" in result["error"]


@pytest.mark.asyncio
async def test_join_challenge_not_active(challenge_manager):
    """アクティブでないチャレンジへの参加テスト"""
    manager, conn = challenge_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.return_value = {
        "id": 1,
        "creator_id": 111,
        "guild_id": 456,
        "name": "完了チャレンジ",
        "description": "",
        "goal_type": "study_minutes",
        "goal_target": 600,
        "duration_days": 14,
        "start_date": date.today() - timedelta(days=14),
        "end_date": date.today(),
        "status": "completed",
        "participant_count": 5,
        "creator_name": "Creator",
        "channel_id": None,
        "xp_multiplier": 1.5,
        "created_at": None,
    }

    result = await manager.join_challenge(
        challenge_id=1,
        user_id=123,
        username="TestUser",
    )

    assert "error" in result
    assert "参加受付" in result["error"]


@pytest.mark.asyncio
async def test_checkin(challenge_manager):
    """チェックインテスト"""
    manager, conn = challenge_manager

    conn.fetchrow.side_effect = [
        # get_challenge
        {
            "id": 1,
            "creator_id": 111,
            "guild_id": 456,
            "name": "テストチャレンジ",
            "description": "",
            "goal_type": "study_minutes",
            "goal_target": 600,
            "duration_days": 14,
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=14),
            "status": "active",
            "participant_count": 3,
            "creator_name": "Creator",
            "channel_id": None,
            "xp_multiplier": 1.5,
            "created_at": None,
        },
        # get_participant
        {
            "challenge_id": 1,
            "user_id": 123,
            "progress": 100,
            "checkins": 2,
            "completed": False,
            "last_checkin_date": None,
            "joined_at": None,
        },
        # checkin result (after transaction)
        {
            "challenge_id": 1,
            "user_id": 123,
            "progress": 160,
            "checkins": 3,
            "completed": False,
            "last_checkin_date": date.today(),
            "joined_at": None,
        },
    ]
    conn.execute.return_value = None

    result = await manager.checkin(
        challenge_id=1,
        user_id=123,
        progress_delta=60,
        note="数学を60分",
    )

    assert "error" not in result
    assert result["progress"] == 160
    assert result["checkins"] == 3
    assert result["completed"] is False
    assert result["challenge_name"] == "テストチャレンジ"


@pytest.mark.asyncio
async def test_checkin_not_participant(challenge_manager):
    """参加していないチャレンジへのチェックインテスト"""
    manager, conn = challenge_manager

    conn.fetchrow.side_effect = [
        # get_challenge
        {
            "id": 1,
            "creator_id": 111,
            "guild_id": 456,
            "name": "テストチャレンジ",
            "description": "",
            "goal_type": "study_minutes",
            "goal_target": 600,
            "duration_days": 14,
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=14),
            "status": "active",
            "participant_count": 3,
            "creator_name": "Creator",
            "channel_id": None,
            "xp_multiplier": 1.5,
            "created_at": None,
        },
        # get_participant (not found)
        None,
    ]

    result = await manager.checkin(
        challenge_id=1,
        user_id=999,
        progress_delta=60,
    )

    assert "error" in result
    assert "参加していません" in result["error"]


@pytest.mark.asyncio
async def test_list_challenges(challenge_manager):
    """チャレンジ一覧テスト"""
    manager, conn = challenge_manager

    conn.fetch.return_value = [
        {
            "id": 1,
            "creator_id": 111,
            "guild_id": 456,
            "name": "チャレンジ1",
            "description": "",
            "goal_type": "study_minutes",
            "goal_target": 600,
            "duration_days": 14,
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=14),
            "status": "active",
            "participant_count": 5,
            "creator_name": "User1",
            "channel_id": None,
            "xp_multiplier": 1.5,
            "created_at": None,
        },
        {
            "id": 2,
            "creator_id": 222,
            "guild_id": 456,
            "name": "チャレンジ2",
            "description": "説明文",
            "goal_type": "session_count",
            "goal_target": 30,
            "duration_days": 30,
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=30),
            "status": "active",
            "participant_count": 10,
            "creator_name": "User2",
            "channel_id": None,
            "xp_multiplier": 2.0,
            "created_at": None,
        },
    ]

    challenges = await manager.list_challenges(guild_id=456)
    assert len(challenges) == 2
    assert challenges[0]["name"] == "チャレンジ1"
    assert challenges[1]["participant_count"] == 10


@pytest.mark.asyncio
async def test_check_expired_challenges(challenge_manager):
    """期限切れチャレンジ自動完了テスト"""
    manager, conn = challenge_manager

    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)

    conn.fetch.return_value = [
        {
            "id": 1,
            "creator_id": 111,
            "guild_id": 456,
            "name": "期限切れ",
            "description": "",
            "goal_type": "study_minutes",
            "goal_target": 600,
            "duration_days": 7,
            "start_date": yesterday - timedelta(days=7),
            "end_date": yesterday,
            "status": "active",
            "participant_count": 3,
            "creator_name": "User1",
            "channel_id": None,
            "xp_multiplier": 1.5,
            "created_at": None,
        },
        {
            "id": 2,
            "creator_id": 222,
            "guild_id": 456,
            "name": "まだ有効",
            "description": "",
            "goal_type": "study_minutes",
            "goal_target": 600,
            "duration_days": 14,
            "start_date": date.today(),
            "end_date": tomorrow,
            "status": "active",
            "participant_count": 5,
            "creator_name": "User2",
            "channel_id": None,
            "xp_multiplier": 1.5,
            "created_at": None,
        },
    ]
    conn.execute.return_value = None

    count = await manager.check_expired_challenges(guild_id=456)
    assert count == 1  # 1つだけ期限切れ
