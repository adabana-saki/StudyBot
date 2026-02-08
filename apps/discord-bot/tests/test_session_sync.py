"""セッション同期 テスト"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import MockAsyncContextManager


@pytest.fixture
def mock_session_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value = MockAsyncContextManager(conn)
    return pool, conn


@pytest.mark.asyncio
async def test_create_session(mock_session_pool):
    from studybot.repositories.session_sync_repository import SessionSyncRepository

    pool, conn = mock_session_pool
    end_time = datetime.now(UTC) + timedelta(minutes=25)
    conn.fetchval.return_value = 1
    repo = SessionSyncRepository(pool)
    result = await repo.create_session(123, "pomodoro", "discord", 25, end_time, "Math")
    assert result == 1


@pytest.mark.asyncio
async def test_get_active_session(mock_session_pool):
    from studybot.repositories.session_sync_repository import SessionSyncRepository

    pool, conn = mock_session_pool
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "session_type": "pomodoro",
        "source_platform": "discord",
        "topic": "Math",
        "duration_minutes": 25,
        "state": "active",
        "started_at": datetime.now(UTC),
        "end_time": datetime.now(UTC) + timedelta(minutes=25),
    }
    repo = SessionSyncRepository(pool)
    result = await repo.get_active_session(123)
    assert result is not None
    assert result["session_type"] == "pomodoro"


@pytest.mark.asyncio
async def test_get_active_session_none(mock_session_pool):
    from studybot.repositories.session_sync_repository import SessionSyncRepository

    pool, conn = mock_session_pool
    conn.fetchrow.return_value = None
    repo = SessionSyncRepository(pool)
    result = await repo.get_active_session(999)
    assert result is None


@pytest.mark.asyncio
async def test_end_session(mock_session_pool):
    from studybot.repositories.session_sync_repository import SessionSyncRepository

    pool, conn = mock_session_pool
    repo = SessionSyncRepository(pool)
    await repo.end_session(1)
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_register_session_service(mock_session_pool):
    from studybot.services.session_sync import SessionSyncService

    pool, conn = mock_session_pool
    conn.fetchval.return_value = 1
    conn.fetchrow.return_value = None
    service = SessionSyncService(pool, redis_client=None)
    result = await service.register_session(
        user_id=123,
        username="TestUser",
        session_type="pomodoro",
        source="discord",
        duration_minutes=25,
        topic="Math",
    )
    assert result["session_id"] == 1
    assert result["session_type"] == "pomodoro"


@pytest.mark.asyncio
async def test_end_session_service(mock_session_pool):
    from studybot.services.session_sync import SessionSyncService

    pool, conn = mock_session_pool
    conn.fetchrow.return_value = {
        "id": 1,
        "session_type": "pomodoro",
        "user_id": 123,
    }
    service = SessionSyncService(pool, redis_client=None)
    result = await service.end_session(123)
    assert result["ended"] is True
