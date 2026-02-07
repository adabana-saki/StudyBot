"""スマホ通知のテスト"""

from datetime import UTC, datetime, timedelta

import pytest

from studybot.managers.nudge_manager import NudgeManager


@pytest.fixture
def nudge_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = NudgeManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_setup_webhook(nudge_manager):
    """Webhook設定テスト"""
    manager, conn = nudge_manager

    conn.execute.return_value = None

    result = await manager.setup_webhook(123, "Test", "https://example.com/webhook")

    assert result.get("success") is True


@pytest.mark.asyncio
async def test_setup_webhook_invalid_url(nudge_manager):
    """無効なURLのエラー"""
    manager, conn = nudge_manager

    result = await manager.setup_webhook(123, "Test", "not-a-url")
    assert "error" in result


@pytest.mark.asyncio
async def test_send_nudge_no_config(nudge_manager):
    """設定なしでの通知送信"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = None  # no config

    result = await manager.send_nudge(123, "test", "テスト")
    assert result is False


@pytest.mark.asyncio
async def test_send_nudge_disabled(nudge_manager):
    """無効化された通知"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = {
        "user_id": 123,
        "webhook_url": "https://example.com/webhook",
        "enabled": False,
    }

    result = await manager.send_nudge(123, "test", "テスト")
    assert result is False


@pytest.mark.asyncio
async def test_toggle(nudge_manager):
    """通知ON/OFF切り替え"""
    manager, conn = nudge_manager

    conn.execute.return_value = "UPDATE 1"

    result = await manager.toggle(123, False)
    assert result is True


@pytest.mark.asyncio
async def test_get_config(nudge_manager):
    """設定取得テスト"""
    manager, conn = nudge_manager

    conn.fetchrow.return_value = {
        "user_id": 123,
        "webhook_url": "https://example.com/webhook",
        "enabled": True,
    }

    config = await manager.get_config(123)
    assert config is not None
    assert config["enabled"] is True


# === Lock/Shield テスト ===


@pytest.mark.asyncio
async def test_start_lock(nudge_manager):
    """ロック作成テスト"""
    manager, conn = nudge_manager

    # アクティブロックなし
    conn.fetchrow.return_value = None
    conn.execute.return_value = None

    # create_lock_session の返り値を設定（2回目のfetchrow呼び出し）
    lock_row = {
        "id": 1,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 20,
        "state": "active",
        "started_at": datetime.now(UTC),
        "ended_at": None,
    }
    # get_active_lock -> None, create_lock_session -> lock_row
    conn.fetchrow.side_effect = [None, lock_row]

    result = await manager.start_lock(123, "Test", 30, coins_bet=20)

    assert "error" not in result
    assert result["session_id"] == 1
    assert result["duration"] == 30
    assert result["coins_bet"] == 20
    assert 123 in manager.active_locks


@pytest.mark.asyncio
async def test_start_lock_already_active(nudge_manager):
    """既存ロックありでのエラー"""
    manager, conn = nudge_manager

    # メモリ上にアクティブロックを設定
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 0,
        "lock_type": "lock",
    }

    result = await manager.start_lock(123, "Test", 30)

    assert "error" in result
    assert "既にアクティブなロック" in result["error"]

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_break_lock(nudge_manager):
    """ロック中断テスト"""
    manager, conn = nudge_manager

    # メモリ上にアクティブロックを設定
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 50,
        "lock_type": "lock",
    }

    broken_row = {
        "id": 1,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 50,
        "state": "broken",
        "started_at": datetime.now(UTC),
        "ended_at": datetime.now(UTC),
    }
    conn.fetchrow.return_value = broken_row

    result = await manager.break_lock(123)

    assert result["broken"] is True
    assert result["coins_lost"] == 50
    assert 123 not in manager.active_locks


@pytest.mark.asyncio
async def test_complete_lock(nudge_manager):
    """ロック完了テスト"""
    manager, conn = nudge_manager

    # メモリ上にアクティブロックを設定
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) + timedelta(minutes=30),
        "coins_bet": 20,
        "lock_type": "lock",
    }

    completed_row = {
        "id": 1,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 20,
        "state": "completed",
        "started_at": datetime.now(UTC),
        "ended_at": datetime.now(UTC),
    }
    conn.fetchrow.return_value = completed_row

    result = await manager.complete_lock(123)

    assert result["completed"] is True
    assert result["coins_earned"] == 15  # COIN_REWARDS["lock_complete"]
    assert result["coins_returned"] == 20
    assert 123 not in manager.active_locks


@pytest.mark.asyncio
async def test_start_shield(nudge_manager):
    """シールド作成テスト"""
    manager, conn = nudge_manager

    # アクティブロックなし
    conn.fetchrow.return_value = None
    conn.execute.return_value = None

    shield_row = {
        "id": 2,
        "user_id": 123,
        "lock_type": "shield",
        "duration_minutes": 60,
        "coins_bet": 0,
        "state": "active",
        "started_at": datetime.now(UTC),
        "ended_at": None,
    }
    # get_active_lock -> None, create_lock_session -> shield_row
    conn.fetchrow.side_effect = [None, shield_row]

    result = await manager.start_shield(123, "Test", 60)

    assert "error" not in result
    assert result["session_id"] == 2
    assert result["duration"] == 60
    assert 123 in manager.active_locks
    assert manager.active_locks[123]["lock_type"] == "shield"

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_get_lock_status(nudge_manager):
    """ロックステータス取得テスト"""
    manager, conn = nudge_manager

    end_time = datetime.now(UTC) + timedelta(minutes=15)
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": end_time,
        "coins_bet": 30,
        "lock_type": "lock",
    }

    status = await manager.get_lock_status(123)

    assert status is not None
    assert status["session_id"] == 1
    assert status["lock_type"] == "lock"
    assert status["coins_bet"] == 30
    assert status["remaining_minutes"] > 0

    # クリーンアップ
    manager.active_locks.pop(123, None)


@pytest.mark.asyncio
async def test_check_locks_expired(nudge_manager):
    """期限切れロックの完了チェック"""
    manager, conn = nudge_manager

    # 期限切れのロックを設定
    manager.active_locks[123] = {
        "session_id": 1,
        "end_time": datetime.now(UTC) - timedelta(minutes=5),
        "coins_bet": 10,
        "lock_type": "lock",
    }

    completed_row = {
        "id": 1,
        "user_id": 123,
        "lock_type": "lock",
        "duration_minutes": 30,
        "coins_bet": 10,
        "state": "completed",
        "started_at": datetime.now(UTC) - timedelta(minutes=35),
        "ended_at": datetime.now(UTC),
    }
    conn.fetchrow.return_value = completed_row

    completed = await manager.check_locks()

    assert len(completed) == 1
    assert completed[0]["completed"] is True
    assert completed[0]["user_id"] == 123
    assert completed[0]["coins_earned"] == 15
    assert 123 not in manager.active_locks
