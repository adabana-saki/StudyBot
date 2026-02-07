"""フォーカスモードのテスト"""

from datetime import UTC, datetime, timedelta

import pytest

from studybot.managers.focus_manager import FocusManager


@pytest.fixture
def focus_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = FocusManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_start_focus(focus_manager):
    """フォーカスセッション開始テスト"""
    manager, conn = focus_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        None,  # get_active_session: no active session
        {  # create_session RETURNING *
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 60,
            "whitelisted_channels": [],
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
    ]

    result = await manager.start_focus(
        user_id=123,
        username="TestUser",
        guild_id=456,
        duration_minutes=60,
    )

    assert "session_id" in result
    assert result["session_id"] == 1
    assert result["duration"] == 60
    assert "end_time" in result
    assert 123 in manager.active_sessions


@pytest.mark.asyncio
async def test_start_focus_already_active(focus_manager):
    """既にセッションがある場合のエラーテスト"""
    manager, conn = focus_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        None,  # get_active_session for first start
        {  # create_session RETURNING * for first start
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 60,
            "whitelisted_channels": [],
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
    ]

    # 最初のセッション開始
    await manager.start_focus(user_id=123, username="TestUser", guild_id=456, duration_minutes=60)

    # 2回目の開始は失敗するべき（メモリ内チェック）
    result = await manager.start_focus(
        user_id=123, username="TestUser", guild_id=456, duration_minutes=30
    )

    assert "error" in result


@pytest.mark.asyncio
async def test_start_focus_invalid_duration(focus_manager):
    """不正な時間指定のテスト"""
    manager, conn = focus_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.return_value = None  # get_active_session

    # 短すぎる
    result = await manager.start_focus(
        user_id=123,
        username="TestUser",
        guild_id=456,
        duration_minutes=5,
    )
    assert "error" in result

    # 長すぎる
    result = await manager.start_focus(
        user_id=123,
        username="TestUser",
        guild_id=456,
        duration_minutes=999,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_end_focus(focus_manager):
    """フォーカス終了テスト"""
    manager, conn = focus_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        None,  # get_active_session
        {  # create_session RETURNING *
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 60,
            "whitelisted_channels": [],
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
        {  # end_session RETURNING *
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 60,
            "whitelisted_channels": [],
            "state": "completed",
            "started_at": datetime.now(UTC),
            "ended_at": datetime.now(UTC),
        },
    ]

    # セッション開始
    await manager.start_focus(user_id=123, username="TestUser", guild_id=456, duration_minutes=60)

    # セッション終了
    result = await manager.end_focus(123)

    assert result["session_id"] == 1
    assert result["duration_planned"] == 60
    assert "duration_actual" in result
    assert 123 not in manager.active_sessions


@pytest.mark.asyncio
async def test_end_focus_no_session(focus_manager):
    """セッションなしで終了"""
    manager, conn = focus_manager

    result = await manager.end_focus(999)
    assert "error" in result


@pytest.mark.asyncio
async def test_add_whitelist(focus_manager):
    """ホワイトリスト追加テスト"""
    manager, conn = focus_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        None,  # get_active_session
        {  # create_session RETURNING *
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 60,
            "whitelisted_channels": [],
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
    ]

    # セッション開始
    await manager.start_focus(user_id=123, username="TestUser", guild_id=456, duration_minutes=60)

    # ホワイトリスト追加
    result = await manager.add_whitelist(123, 111222333)

    assert result["success"] is True
    assert result["channel_id"] == 111222333
    assert result["whitelist_count"] == 1
    assert 111222333 in manager.active_sessions[123]["whitelisted_channels"]


@pytest.mark.asyncio
async def test_add_whitelist_no_session(focus_manager):
    """セッションなしでホワイトリスト追加"""
    manager, conn = focus_manager

    result = await manager.add_whitelist(999, 111222333)
    assert "error" in result


@pytest.mark.asyncio
async def test_add_whitelist_duplicate(focus_manager):
    """既に追加済みのチャンネルを追加"""
    manager, conn = focus_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        None,
        {
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 60,
            "whitelisted_channels": [],
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
    ]

    await manager.start_focus(user_id=123, username="TestUser", guild_id=456, duration_minutes=60)

    # 1回目は成功
    await manager.add_whitelist(123, 111222333)

    # 2回目は重複エラー
    result = await manager.add_whitelist(123, 111222333)
    assert "error" in result


@pytest.mark.asyncio
async def test_get_status(focus_manager):
    """ステータス取得テスト"""
    manager, conn = focus_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        None,
        {
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 60,
            "whitelisted_channels": [],
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
    ]

    await manager.start_focus(user_id=123, username="TestUser", guild_id=456, duration_minutes=60)

    status = manager.get_status(123)

    assert status is not None
    assert status["session_id"] == 1
    assert status["duration_minutes"] == 60
    assert 0 <= status["progress"] <= 1
    assert status["remaining_seconds"] > 0


@pytest.mark.asyncio
async def test_get_status_no_session(focus_manager):
    """セッションなしのステータス"""
    manager, conn = focus_manager
    assert manager.get_status(999) is None


@pytest.mark.asyncio
async def test_check_sessions_expired(focus_manager):
    """期限切れセッションのチェックテスト"""
    manager, conn = focus_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        None,  # get_active_session
        {  # create_session RETURNING *
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 10,
            "whitelisted_channels": [],
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
        {  # end_session RETURNING * (called by check_sessions)
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 10,
            "whitelisted_channels": [],
            "state": "completed",
            "started_at": datetime.now(UTC),
            "ended_at": datetime.now(UTC),
        },
    ]

    # セッション開始
    await manager.start_focus(user_id=123, username="TestUser", guild_id=456, duration_minutes=10)

    # end_timeを過去に設定して期限切れをシミュレート
    manager.active_sessions[123]["end_time"] = datetime.now(UTC) - timedelta(minutes=1)

    # チェック実行
    expired = await manager.check_sessions()

    assert len(expired) == 1
    assert expired[0]["user_id"] == 123
    assert expired[0]["session_id"] == 1
    assert expired[0]["duration_minutes"] == 10
    assert 123 not in manager.active_sessions


@pytest.mark.asyncio
async def test_check_sessions_none_expired(focus_manager):
    """期限切れセッションがない場合のテスト"""
    manager, conn = focus_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        None,
        {
            "id": 1,
            "user_id": 123,
            "guild_id": 456,
            "duration_minutes": 60,
            "whitelisted_channels": [],
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
    ]

    await manager.start_focus(user_id=123, username="TestUser", guild_id=456, duration_minutes=60)

    # end_timeは60分後なのでまだ期限切れではない
    expired = await manager.check_sessions()

    assert len(expired) == 0
    assert 123 in manager.active_sessions
