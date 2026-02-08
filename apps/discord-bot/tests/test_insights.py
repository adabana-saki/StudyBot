"""インサイト テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import MockAsyncContextManager


@pytest.fixture
def mock_insights_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value = MockAsyncContextManager(conn)
    conn.transaction = MagicMock(return_value=MockAsyncContextManager(conn))
    return pool, conn


@pytest.mark.asyncio
async def test_get_weekly_study_data(mock_insights_pool):
    from studybot.repositories.insights_repository import InsightsRepository

    pool, conn = mock_insights_pool
    conn.fetch.return_value = []
    repo = InsightsRepository(pool)
    result = await repo.get_weekly_study_data(123, days=7)
    assert "study_logs" in result
    assert "wellness_logs" in result


@pytest.mark.asyncio
async def test_save_insights(mock_insights_pool):
    from studybot.repositories.insights_repository import InsightsRepository

    pool, conn = mock_insights_pool
    repo = InsightsRepository(pool)
    await repo.save_insights(
        123, [{"type": "pattern", "title": "Test", "body": "Test body", "confidence": 0.8}]
    )
    assert conn.execute.called


@pytest.mark.asyncio
async def test_get_user_insights(mock_insights_pool):
    from studybot.repositories.insights_repository import InsightsRepository

    pool, conn = mock_insights_pool
    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123,
            "insight_type": "pattern",
            "title": "Test",
            "body": "Body",
            "data": "{}",
            "confidence": 0.8,
            "active": True,
            "generated_at": None,
        }
    ]
    repo = InsightsRepository(pool)
    result = await repo.get_user_insights(123)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_compute_stats():
    from studybot.managers.insights_manager import InsightsManager

    pool = MagicMock()
    manager = InsightsManager(pool)
    raw_data = {
        "study_logs": [{"duration_minutes": 30, "logged_at": None}],
        "pomodoro_sessions": [{"total_work_seconds": 1500}],
        "wellness_logs": [{"mood": 4, "energy": 3, "stress": 2}],
        "todos": [{"status": "completed"}, {"status": "pending"}],
        "flashcard_reviews": [{"quality": 4}, {"quality": 2}],
        "focus_sessions": [{"state": "completed"}],
    }
    stats = manager._compute_stats(raw_data)
    assert stats["total_study_minutes"] == 30
    assert stats["total_pomodoro_minutes"] == 25
    assert stats["todo_completion_rate"] == 50


@pytest.mark.asyncio
async def test_generate_fallback():
    from studybot.managers.insights_manager import InsightsManager

    pool = MagicMock()
    manager = InsightsManager(pool)
    stats = {
        "total_combined_minutes": 400,
        "avg_stress": 4.0,
        "todo_completion_rate": 90,
        "todo_completed": 9,
        "todo_total": 10,
        "hour_distribution": [0] * 6 + [100] * 6 + [0] * 12,
    }
    insights = manager._generate_fallback(stats)
    assert len(insights) >= 2


@pytest.mark.asyncio
async def test_get_reports(mock_insights_pool):
    from studybot.repositories.insights_repository import InsightsRepository

    pool, conn = mock_insights_pool
    conn.fetch.return_value = []
    repo = InsightsRepository(pool)
    result = await repo.get_reports(123)
    assert result == []


@pytest.mark.asyncio
async def test_get_active_user_ids(mock_insights_pool):
    from studybot.repositories.insights_repository import InsightsRepository

    pool, conn = mock_insights_pool
    conn.fetch.return_value = [{"user_id": 123}, {"user_id": 456}]
    repo = InsightsRepository(pool)
    result = await repo.get_active_user_ids()
    assert len(result) == 2
