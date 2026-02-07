"""テスト共通フィクスチャ"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.auth.jwt_handler import create_access_token


@pytest.fixture
def mock_pool():
    """モックDB接続プール"""
    pool = MagicMock()
    conn = AsyncMock()

    class MockAsyncCtx:
        def __init__(self, return_value):
            self._return_value = return_value

        async def __aenter__(self):
            return self._return_value

        async def __aexit__(self, *args):
            return False

    pool.acquire.return_value = MockAsyncCtx(conn)
    conn.transaction = MagicMock(return_value=MockAsyncCtx(conn))
    return pool, conn


@pytest.fixture
def test_token():
    """テスト用JWTトークン"""
    return create_access_token(123456789, "TestUser")


@pytest.fixture
def auth_headers(test_token):
    """認証ヘッダー"""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def app(mock_pool):
    """テスト用FastAPIアプリ"""
    pool, _ = mock_pool
    with patch("api.database.pool", pool):
        with patch("api.database.get_pool", return_value=pool):
            from main import app

            yield app


@pytest.fixture
def client(app):
    """テストクライアント"""
    return TestClient(app)
