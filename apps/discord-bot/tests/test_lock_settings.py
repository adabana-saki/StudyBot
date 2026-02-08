"""ロック設定・アンロックコードのテスト"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from studybot.repositories.lock_settings_repository import LockSettingsRepository


@pytest.fixture
def lock_repo(mock_db_pool):
    pool, conn = mock_db_pool
    repo = LockSettingsRepository(pool)
    return repo, conn


@pytest.mark.asyncio
async def test_get_settings_none(lock_repo):
    """設定未登録の場合Noneを返す"""
    repo, conn = lock_repo
    conn.fetchrow.return_value = None

    result = await repo.get_settings(123)
    assert result is None


@pytest.mark.asyncio
async def test_get_settings(lock_repo):
    """設定取得テスト"""
    repo, conn = lock_repo
    conn.fetchrow.return_value = {
        "user_id": 123,
        "default_unlock_level": 3,
        "default_duration": 45,
        "default_coin_bet": 20,
        "block_categories": ["sns", "games"],
        "custom_blocked_urls": ["https://example.com"],
        "updated_at": datetime.now(UTC),
    }

    result = await repo.get_settings(123)
    assert result is not None
    assert result["default_unlock_level"] == 3
    assert result["default_duration"] == 45
    assert result["default_coin_bet"] == 20
    assert "sns" in result["block_categories"]


@pytest.mark.asyncio
async def test_upsert_settings(lock_repo):
    """設定作成/更新テスト"""
    repo, conn = lock_repo
    conn.fetchrow.return_value = {
        "user_id": 123,
        "default_unlock_level": 2,
        "default_duration": 60,
        "default_coin_bet": 30,
        "block_categories": ["sns"],
        "custom_blocked_urls": [],
        "updated_at": datetime.now(UTC),
    }
    conn.execute.return_value = None

    result = await repo.upsert_settings(
        user_id=123,
        default_unlock_level=2,
        default_duration=60,
        default_coin_bet=30,
        block_categories=["sns"],
    )
    assert result["default_unlock_level"] == 2
    assert result["default_duration"] == 60


@pytest.mark.asyncio
async def test_create_unlock_code_confirmation(lock_repo):
    """確認コード生成テスト（6桁数字）"""
    repo, conn = lock_repo
    conn.execute.return_value = None

    code = await repo.create_unlock_code(123, 1, "confirmation", code_length=6)

    assert len(code) == 6
    assert code.isdigit()  # 数字のみ


@pytest.mark.asyncio
async def test_create_unlock_code_dm(lock_repo):
    """DMコード生成テスト（8文字英数字）"""
    repo, conn = lock_repo
    conn.execute.return_value = None

    code = await repo.create_unlock_code(123, 1, "dm", code_length=8)

    assert len(code) == 8
    assert code.isalnum()  # 英数字のみ


@pytest.mark.asyncio
async def test_create_unlock_code_study(lock_repo):
    """学習完了コード生成テスト（12文字英数字）"""
    repo, conn = lock_repo
    conn.execute.return_value = None

    code = await repo.create_unlock_code(123, 1, "study", code_length=12)

    assert len(code) == 12
    assert code.isalnum()


@pytest.mark.asyncio
async def test_get_valid_code_found(lock_repo):
    """有効なコード検証テスト"""
    repo, conn = lock_repo
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "session_id": 1,
        "code": "ABC123XY",
        "code_type": "dm",
        "expires_at": datetime.now(UTC) + timedelta(minutes=10),
        "used": False,
        "created_at": datetime.now(UTC),
    }

    result = await repo.get_valid_code(123, 1, "ABC123XY")
    assert result is not None
    assert result["code"] == "ABC123XY"
    assert result["used"] is False


@pytest.mark.asyncio
async def test_get_valid_code_not_found(lock_repo):
    """無効なコード検証テスト"""
    repo, conn = lock_repo
    conn.fetchrow.return_value = None

    result = await repo.get_valid_code(123, 1, "WRONGCODE")
    assert result is None


@pytest.mark.asyncio
async def test_use_code(lock_repo):
    """コード使用済み更新テスト"""
    repo, conn = lock_repo
    conn.execute.return_value = None

    await repo.use_code(1)
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_code_request(lock_repo):
    """コードリクエスト作成テスト"""
    repo, conn = lock_repo
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "session_id": 1,
        "status": "pending",
        "created_at": datetime.now(UTC),
    }

    result = await repo.create_code_request(123, 1)
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_get_pending_requests(lock_repo):
    """保留中リクエスト取得テスト"""
    repo, conn = lock_repo
    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123,
            "session_id": 1,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "unlock_level": 3,
            "lock_type": "lock",
        }
    ]

    results = await repo.get_pending_requests()
    assert len(results) == 1
    assert results[0]["unlock_level"] == 3


@pytest.mark.asyncio
async def test_fulfill_request(lock_repo):
    """リクエストfulfill更新テスト"""
    repo, conn = lock_repo
    conn.execute.return_value = None

    await repo.fulfill_request(1)
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_lock_history(lock_repo):
    """ロック履歴取得テスト"""
    repo, conn = lock_repo
    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123,
            "lock_type": "lock",
            "duration_minutes": 30,
            "coins_bet": 20,
            "unlock_level": 2,
            "state": "completed",
            "started_at": datetime.now(UTC) - timedelta(hours=1),
            "ended_at": datetime.now(UTC),
        },
        {
            "id": 2,
            "user_id": 123,
            "lock_type": "shield",
            "duration_minutes": 60,
            "coins_bet": 0,
            "unlock_level": 1,
            "state": "broken",
            "started_at": datetime.now(UTC) - timedelta(hours=2),
            "ended_at": datetime.now(UTC) - timedelta(hours=1),
        },
    ]

    results = await repo.get_lock_history(123)
    assert len(results) == 2
    assert results[0]["state"] == "completed"
    assert results[1]["state"] == "broken"


@pytest.mark.asyncio
async def test_code_uniqueness():
    """コード生成のユニーク性テスト"""
    pool = MagicMock()
    conn = AsyncMock()

    class MockACM:
        def __init__(self, rv):
            self._rv = rv

        async def __aenter__(self):
            return self._rv

        async def __aexit__(self, *a):
            return False

    pool.acquire.return_value = MockACM(conn)
    conn.execute.return_value = None

    repo = LockSettingsRepository(pool)

    codes = set()
    for _ in range(100):
        code = await repo.create_unlock_code(123, 1, "dm", code_length=8)
        codes.add(code)

    # 100個中、ほぼ全てがユニークであること（衝突確率は無視できるレベル）
    assert len(codes) >= 95
