"""VCスタディ追跡のテスト"""

import pytest

from studybot.managers.voice_manager import VoiceManager


@pytest.fixture
def voice_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = VoiceManager(pool)
    return manager, conn


def test_start_session(voice_manager):
    """セッション開始テスト"""
    manager, conn = voice_manager
    manager.start_session(123, 456, 789)
    assert manager.is_tracking(123)
    sessions = manager.get_active_sessions()
    assert 123 in sessions
    assert sessions[123]["guild_id"] == 456
    assert sessions[123]["channel_id"] == 789


def test_is_tracking_no_session(voice_manager):
    """追跡していないユーザーのチェック"""
    manager, conn = voice_manager
    assert not manager.is_tracking(999)


@pytest.mark.asyncio
async def test_end_session_too_short(voice_manager):
    """短すぎるセッションは記録されない"""
    manager, conn = voice_manager
    manager.start_session(123, 456, 789)
    # セッションは即座に終了するので5分未満
    result = await manager.end_session(123, min_minutes=5)
    assert result is None
    assert not manager.is_tracking(123)


@pytest.mark.asyncio
async def test_end_session_no_session(voice_manager):
    """セッションがない場合"""
    manager, conn = voice_manager
    result = await manager.end_session(999)
    assert result is None


@pytest.mark.asyncio
async def test_get_stats(voice_manager):
    """VC統計取得テスト"""
    manager, conn = voice_manager
    conn.fetchrow.return_value = {
        "total_minutes": 120,
        "session_count": 5,
        "avg_minutes": 24,
    }
    stats = await manager.get_stats(123, 456)
    assert stats["total_minutes"] == 120
    assert stats["session_count"] == 5


@pytest.mark.asyncio
async def test_get_ranking(voice_manager):
    """VCランキング取得テスト"""
    manager, conn = voice_manager
    conn.fetch.return_value = [
        {"user_id": 1, "username": "User1", "total_minutes": 200, "session_count": 10},
        {"user_id": 2, "username": "User2", "total_minutes": 150, "session_count": 8},
    ]
    ranking = await manager.get_ranking(456)
    assert len(ranking) == 2
    assert ranking[0]["total_minutes"] == 200


def test_get_active_sessions_empty(voice_manager):
    """アクティブセッションが空の場合"""
    manager, conn = voice_manager
    sessions = manager.get_active_sessions()
    assert len(sessions) == 0
