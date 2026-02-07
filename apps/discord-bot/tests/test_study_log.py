"""学習ログ & 統計のテスト"""

from datetime import date, timedelta

import pytest

from studybot.managers.study_manager import StudyManager


@pytest.fixture
def study_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = StudyManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_log_study(study_manager):
    """学習ログ記録テスト"""
    manager, conn = study_manager

    conn.execute.return_value = None  # ensure_user, update_stats_cache
    conn.fetchval.return_value = 42  # log_id

    log_id = await manager.log_study(
        user_id=123,
        username="Test",
        guild_id=456,
        duration_minutes=30,
        topic="数学",
    )

    assert log_id == 42


@pytest.mark.asyncio
async def test_get_stats(study_manager):
    """統計取得テスト"""
    manager, conn = study_manager

    conn.fetchrow.return_value = {
        "total_minutes": 150,
        "session_count": 5,
        "avg_minutes": 30,
    }

    stats = await manager.get_stats(123, 456, "weekly")
    assert stats["total_minutes"] == 150
    assert stats["session_count"] == 5
    assert stats["avg_minutes"] == 30


@pytest.mark.asyncio
async def test_generate_chart_no_data(study_manager):
    """データなしのチャート生成"""
    manager, conn = study_manager

    conn.fetch.return_value = []  # no data

    result = await manager.generate_chart(123, 456, "line", 14)
    assert result is None


@pytest.mark.asyncio
async def test_generate_chart_with_data(study_manager):
    """データありのチャート生成"""
    manager, conn = study_manager

    today = date.today()
    conn.fetch.return_value = [
        {"study_date": today - timedelta(days=2), "total_minutes": 30},
        {"study_date": today - timedelta(days=1), "total_minutes": 45},
        {"study_date": today, "total_minutes": 60},
    ]

    result = await manager.generate_chart(123, 456, "line", 14)
    assert result is not None
    # BytesIO should have PNG data
    data = result.read()
    assert len(data) > 0
    assert data[:4] == b"\x89PNG"  # PNG magic bytes
