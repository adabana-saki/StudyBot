"""アクティビティリポジトリ テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import MockAsyncContextManager


@pytest.fixture
def mock_activity_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value = MockAsyncContextManager(conn)
    return pool, conn


@pytest.mark.asyncio
async def test_save_event(mock_activity_pool):
    from studybot.repositories.activity_repository import ActivityRepository

    pool, conn = mock_activity_pool
    repo = ActivityRepository(pool)
    await repo.save_event(123, 456, "study_start", {"topic": "Math"})
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_recent(mock_activity_pool):
    from studybot.repositories.activity_repository import ActivityRepository

    pool, conn = mock_activity_pool
    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123,
            "username": "TestUser",
            "event_type": "study_start",
            "event_data": '{"topic": "Math"}',
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]
    repo = ActivityRepository(pool)
    result = await repo.get_recent(456, limit=10)
    assert len(result) == 1
    assert result[0]["event_type"] == "study_start"


@pytest.mark.asyncio
async def test_get_recent_empty(mock_activity_pool):
    from studybot.repositories.activity_repository import ActivityRepository

    pool, conn = mock_activity_pool
    conn.fetch.return_value = []
    repo = ActivityRepository(pool)
    result = await repo.get_recent(456)
    assert result == []


@pytest.mark.asyncio
async def test_get_studying_now(mock_activity_pool):
    from studybot.repositories.activity_repository import ActivityRepository

    pool, conn = mock_activity_pool
    conn.fetch.return_value = [
        {
            "user_id": 123,
            "username": "Studier",
            "event_type": "study_start",
            "event_data": "{}",
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]
    repo = ActivityRepository(pool)
    result = await repo.get_studying_now(456)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_studying_now_empty(mock_activity_pool):
    from studybot.repositories.activity_repository import ActivityRepository

    pool, conn = mock_activity_pool
    conn.fetch.return_value = []
    repo = ActivityRepository(pool)
    result = await repo.get_studying_now(456)
    assert result == []
