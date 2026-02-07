"""ポモドーロタイマーのテスト"""

import pytest

from studybot.managers.pomodoro_manager import PomodoroManager


@pytest.fixture
def pomodoro_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = PomodoroManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_start_session(pomodoro_manager):
    """セッション開始テスト"""
    manager, conn = pomodoro_manager

    conn.fetchrow.return_value = None  # no active session
    conn.fetchval.return_value = 1  # session_id
    conn.execute.return_value = None  # ensure_user

    result = await manager.start_session(
        user_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
        topic="数学",
        work_minutes=25,
        break_minutes=5,
    )

    assert "session_id" in result
    assert result["session_id"] == 1
    assert result["topic"] == "数学"
    assert result["work_minutes"] == 25
    assert 123 in manager.active_timers


@pytest.mark.asyncio
async def test_start_session_already_active(pomodoro_manager):
    """既存セッションがある場合のエラーテスト"""
    manager, conn = pomodoro_manager

    conn.execute.return_value = None
    conn.fetchrow.return_value = {"id": 1, "state": "working"}  # active session exists

    result = await manager.start_session(
        user_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
        topic="数学",
    )

    assert "error" in result


@pytest.mark.asyncio
async def test_pause_session(pomodoro_manager):
    """一時停止テスト"""
    manager, conn = pomodoro_manager

    # まずセッションを作成
    conn.fetchrow.return_value = None
    conn.fetchval.return_value = 1
    conn.execute.return_value = None

    await manager.start_session(
        user_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
    )

    result = await manager.pause_session(123)
    assert result.get("success") is True
    assert manager.active_timers[123]["state"] == "paused"


@pytest.mark.asyncio
async def test_pause_no_session(pomodoro_manager):
    """セッションなしで一時停止"""
    manager, conn = pomodoro_manager
    result = await manager.pause_session(999)
    assert "error" in result


@pytest.mark.asyncio
async def test_resume_session(pomodoro_manager):
    """再開テスト"""
    manager, conn = pomodoro_manager

    conn.fetchrow.return_value = None
    conn.fetchval.return_value = 1
    conn.execute.return_value = None

    await manager.start_session(
        user_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
    )
    await manager.pause_session(123)

    result = await manager.resume_session(123)
    assert result.get("success") is True
    assert manager.active_timers[123]["state"] == "working"


@pytest.mark.asyncio
async def test_stop_session(pomodoro_manager):
    """停止テスト"""
    manager, conn = pomodoro_manager

    conn.fetchrow.return_value = None
    conn.fetchval.return_value = 1
    conn.execute.return_value = None

    await manager.start_session(
        user_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
        topic="英語",
    )

    result = await manager.stop_session(123)
    assert result["topic"] == "英語"
    assert "total_minutes" in result
    assert 123 not in manager.active_timers


@pytest.mark.asyncio
async def test_get_status(pomodoro_manager):
    """ステータス取得テスト"""
    manager, conn = pomodoro_manager

    conn.fetchrow.return_value = None
    conn.fetchval.return_value = 1
    conn.execute.return_value = None

    await manager.start_session(
        user_id=123,
        username="Test",
        guild_id=456,
        channel_id=789,
        work_minutes=25,
    )

    status = manager.get_status(123)
    assert status is not None
    assert status["state"] == "working"
    assert status["work_minutes"] == 25
    assert 0 <= status["progress"] <= 1


@pytest.mark.asyncio
async def test_get_status_no_session(pomodoro_manager):
    """セッションなしのステータス"""
    manager, conn = pomodoro_manager
    assert manager.get_status(999) is None
