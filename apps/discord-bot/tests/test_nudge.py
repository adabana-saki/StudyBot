"""スマホ通知のテスト"""

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
