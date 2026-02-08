"""テスト共通フィクスチャ"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.auth.jwt_handler import create_access_token


class MockAsyncCtx:
    """非同期コンテキストマネージャモック"""

    def __init__(self, return_value):
        self._return_value = return_value

    async def __aenter__(self):
        return self._return_value

    async def __aexit__(self, *args):
        return False


@pytest.fixture
def mock_pool():
    """モックDB接続プール"""
    pool = MagicMock()
    conn = AsyncMock()
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
    # pool変数のみパッチ。get_pool()は呼び出し時に
    # api.database.pool を動的に読むのでパッチ不要。
    # get_poolをパッチするとルートモジュールが古い参照を
    # 保持し2番目以降のテストが壊れる。
    with patch("api.database.pool", pool):
        from main import app

        yield app


@pytest.fixture(autouse=True)
def _reset_rate_limiter(app):
    """各テスト前にレート制限をリセット"""
    from api.middleware.rate_limiter import RateLimitMiddleware

    for middleware in app.user_middleware:
        if middleware.cls is RateLimitMiddleware:
            break
    # app.middleware_stack 内のインスタンスをリセット
    stack = app.middleware_stack
    while stack:
        if isinstance(stack, RateLimitMiddleware):
            stack._requests.clear()
            break
        stack = getattr(stack, "app", None)


@pytest.fixture
def client(app):
    """テストクライアント"""
    return TestClient(app)
