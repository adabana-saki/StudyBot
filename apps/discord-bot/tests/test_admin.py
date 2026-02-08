"""管理者Cogのテスト"""

import pytest

from studybot.managers.admin_manager import AdminManager


@pytest.fixture
def admin_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = AdminManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_get_server_stats(admin_manager):
    """サーバー統計取得テスト"""
    manager, conn = admin_manager

    conn.fetchval.side_effect = [
        10,  # member_count
        25,  # task_count
        5,  # raid_count
    ]
    conn.fetchrow.side_effect = [
        {"total_minutes": 5000, "session_count": 200},  # total_study
        {"total_minutes": 500, "active_members": 5},  # weekly
    ]

    stats = await manager.get_server_stats(456)
    assert stats["member_count"] == 10
    assert stats["total_minutes"] == 5000
    assert stats["total_sessions"] == 200
    assert stats["weekly_minutes"] == 500
    assert stats["weekly_active_members"] == 5
    assert stats["tasks_completed"] == 25
    assert stats["raids_completed"] == 5


@pytest.mark.asyncio
async def test_reset_user(admin_manager):
    """ユーザーリセットテスト"""
    manager, conn = admin_manager
    conn.execute.return_value = None

    result = await manager.reset_user(123)
    assert result is True
    # execute が複数回呼ばれることを確認（各テーブルのリセット）
    assert conn.execute.call_count >= 3


@pytest.mark.asyncio
async def test_update_setting(admin_manager):
    """サーバー設定更新テスト"""
    manager, conn = admin_manager
    conn.execute.return_value = None
    conn.fetchrow.return_value = {
        "guild_id": 456,
        "study_channels": [123],
        "vc_channels": [],
        "admin_role_id": None,
        "nudge_enabled": True,
        "vc_tracking_enabled": True,
        "min_vc_minutes": 5,
        "updated_at": None,
    }

    result = await manager.update_setting(456, "study_channels", [123])
    assert result["guild_id"] == 456
    assert result["study_channels"] == [123]
