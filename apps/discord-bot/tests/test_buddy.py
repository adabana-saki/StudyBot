"""バディマッチング テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import MockAsyncContextManager


@pytest.fixture
def mock_buddy_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value = MockAsyncContextManager(conn)
    return pool, conn


@pytest.mark.asyncio
async def test_get_profile(mock_buddy_pool):
    from studybot.repositories.buddy_repository import BuddyRepository

    pool, conn = mock_buddy_pool
    conn.fetchrow.return_value = {
        "user_id": 123,
        "subjects": ["math"],
        "preferred_times": ["morning"],
        "study_style": "focused",
        "active": True,
        "updated_at": None,
    }
    repo = BuddyRepository(pool)
    result = await repo.get_profile(123)
    assert result is not None
    assert result["study_style"] == "focused"


@pytest.mark.asyncio
async def test_get_profile_not_found(mock_buddy_pool):
    from studybot.repositories.buddy_repository import BuddyRepository

    pool, conn = mock_buddy_pool
    conn.fetchrow.return_value = None
    repo = BuddyRepository(pool)
    result = await repo.get_profile(999)
    assert result is None


@pytest.mark.asyncio
async def test_upsert_profile(mock_buddy_pool):
    from studybot.repositories.buddy_repository import BuddyRepository

    pool, conn = mock_buddy_pool
    repo = BuddyRepository(pool)
    await repo.upsert_profile(123, ["math", "english"], ["morning"], "focused")
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_match(mock_buddy_pool):
    from studybot.repositories.buddy_repository import BuddyRepository

    pool, conn = mock_buddy_pool
    conn.fetchval.return_value = 1
    repo = BuddyRepository(pool)
    result = await repo.create_match(123, 456, 789, "math", 0.85)
    assert result == 1


@pytest.mark.asyncio
async def test_compatibility_calculation():
    from studybot.managers.buddy_manager import BuddyManager

    pool = MagicMock()
    manager = BuddyManager(pool)
    profile_a = {
        "subjects": ["math", "english"],
        "preferred_times": ["morning"],
        "study_style": "focused",
    }
    profile_b = {
        "subjects": ["math", "physics"],
        "preferred_times": ["morning"],
        "study_style": "focused",
    }
    score = manager._calculate_compatibility(profile_a, profile_b)
    assert 0 <= score <= 1.0


@pytest.mark.asyncio
async def test_compatibility_identical():
    from studybot.managers.buddy_manager import BuddyManager

    pool = MagicMock()
    manager = BuddyManager(pool)
    profile = {"subjects": ["math"], "preferred_times": ["morning"], "study_style": "focused"}
    score = manager._calculate_compatibility(profile, profile)
    assert score > 0.8


@pytest.mark.asyncio
async def test_get_active_matches(mock_buddy_pool):
    from studybot.repositories.buddy_repository import BuddyRepository

    pool, conn = mock_buddy_pool
    conn.fetch.return_value = []
    repo = BuddyRepository(pool)
    result = await repo.get_active_matches(123)
    assert result == []


@pytest.mark.asyncio
async def test_end_match(mock_buddy_pool):
    from studybot.repositories.buddy_repository import BuddyRepository

    pool, conn = mock_buddy_pool
    repo = BuddyRepository(pool)
    await repo.end_match(1)
    conn.execute.assert_called_once()
