"""投資市場 API ルートテスト"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from tests.conftest import MockAsyncCtx


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value = MockAsyncCtx(conn)
    conn.transaction = MagicMock(return_value=MockAsyncCtx(conn))
    return pool, conn


@pytest.fixture
def app(mock_pool):
    pool, _ = mock_pool
    with patch("api.database.pool", pool):
        from main import app

        yield app


@pytest.fixture
def _reset_rate_limiter(app):
    from api.middleware.rate_limiter import RateLimitMiddleware

    stack = app.middleware_stack
    while stack:
        if isinstance(stack, RateLimitMiddleware):
            stack._requests.clear()
            break
        stack = getattr(stack, "app", None)


@pytest.fixture
def client(app, _reset_rate_limiter):
    return TestClient(app)


@pytest.fixture
def test_token():
    from api.auth.jwt_handler import create_access_token

    return create_access_token(123456789, "TestUser")


@pytest.fixture
def auth_headers(test_token):
    return {"Authorization": f"Bearer {test_token}"}


class TestStocks:
    def test_get_stocks(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "symbol": "MATH",
                "name": "数学株",
                "topic_keyword": "数学",
                "description": "テスト",
                "emoji": "📐",
                "sector": "理系",
                "base_price": 100,
                "current_price": 110,
                "previous_close": 100,
                "total_shares": 10000,
                "circulating_shares": 50,
                "active": True,
                "listed_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        ]

        resp = client.get("/api/market/stocks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "MATH"
        assert data[0]["change_pct"] == 10.0

    def test_get_stock_detail(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": 1,
            "symbol": "CODE",
            "name": "プログラミング株",
            "topic_keyword": "プログラミング",
            "description": "テスト",
            "emoji": "💻",
            "sector": "技術",
            "base_price": 100,
            "current_price": 150,
            "previous_close": 130,
            "total_shares": 10000,
            "circulating_shares": 200,
            "active": True,
            "listed_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        conn.fetch.return_value = [
            {
                "price": 140,
                "volume": 10,
                "study_minutes": 100,
                "study_sessions": 5,
                "recorded_date": datetime.now(UTC).date(),
            },
        ]

        resp = client.get("/api/market/stocks/CODE", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "CODE"
        assert data["current_price"] == 150
        assert len(data["history"]) == 1

    def test_get_stock_not_found(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.get("/api/market/stocks/INVALID", headers=auth_headers)
        assert resp.status_code == 404

    def test_buy_stock_success(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.side_effect = [
            # Stock lookup
            {
                "id": 1,
                "symbol": "MATH",
                "name": "数学株",
                "topic_keyword": "数学",
                "description": "",
                "emoji": "📐",
                "sector": "理系",
                "base_price": 100,
                "current_price": 100,
                "previous_close": 100,
                "total_shares": 10000,
                "circulating_shares": 0,
                "active": True,
                "listed_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
            # Spend coins
            {"balance": 900},
            # Existing holding check
            None,
        ]
        conn.execute.return_value = None

        resp = client.post(
            "/api/market/stocks/MATH/buy",
            json={"shares": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["shares"] == 1
        assert data["total"] == 100

    def test_buy_stock_insufficient_coins(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.side_effect = [
            {
                "id": 1,
                "symbol": "MATH",
                "name": "数学株",
                "topic_keyword": "数学",
                "description": "",
                "emoji": "📐",
                "sector": "理系",
                "base_price": 100,
                "current_price": 100,
                "previous_close": 100,
                "total_shares": 10000,
                "circulating_shares": 0,
                "active": True,
                "listed_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
            None,  # Spend fails
        ]

        resp = client.post(
            "/api/market/stocks/MATH/buy",
            json={"shares": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_buy_stock_invalid_shares(self, client, auth_headers, mock_pool):
        resp = client.post(
            "/api/market/stocks/MATH/buy",
            json={"shares": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_sell_stock_success(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.side_effect = [
            # Stock lookup
            {
                "id": 1,
                "symbol": "MATH",
                "name": "数学株",
                "topic_keyword": "数学",
                "description": "",
                "emoji": "📐",
                "sector": "理系",
                "base_price": 100,
                "current_price": 120,
                "previous_close": 100,
                "total_shares": 10000,
                "circulating_shares": 10,
                "active": True,
                "listed_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
            # Holding check
            {
                "shares": 5,
                "avg_buy_price": 100,
                "total_invested": 500,
                "user_id": 123456789,
                "stock_id": 1,
                "updated_at": datetime.now(UTC),
            },
            # Balance after sell
            {"balance": 1240},
        ]
        conn.execute.return_value = None

        resp = client.post(
            "/api/market/stocks/MATH/sell",
            json={"shares": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["shares"] == 2
        assert data["total"] == 240
        assert data["profit"] == 40

    def test_get_portfolio(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 123456789,
                "stock_id": 1,
                "shares": 10,
                "avg_buy_price": 100,
                "total_invested": 1000,
                "symbol": "MATH",
                "name": "数学株",
                "emoji": "📐",
                "current_price": 120,
                "sector": "理系",
                "updated_at": datetime.now(UTC),
            },
        ]

        resp = client.get("/api/market/portfolio", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["holdings"]) == 1
        assert data["total_value"] == 1200
        assert data["total_profit"] == 200

    def test_get_transactions(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchval.return_value = 1
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 123456789,
                "stock_id": 1,
                "transaction_type": "buy",
                "shares": 5,
                "price_per_share": 100,
                "total_amount": 500,
                "created_at": datetime.now(UTC),
                "symbol": "MATH",
                "name": "数学株",
                "emoji": "📐",
            },
        ]

        resp = client.get("/api/market/transactions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1


class TestSavings:
    def test_get_savings(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 123456789,
                "account_type": "regular",
                "balance": 500,
                "interest_rate": 0.001,
                "lock_days": 0,
                "maturity_date": None,
                "total_interest_earned": 10,
                "last_interest_at": datetime.now(UTC),
                "created_at": datetime.now(UTC),
            },
        ]

        resp = client.get("/api/market/savings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_savings"] == 500
        assert len(data["accounts"]) == 1

    def test_deposit(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.side_effect = [
            {"balance": 900},  # spend
            {
                "id": 1,
                "user_id": 123456789,
                "account_type": "regular",
                "balance": 100,
                "interest_rate": 0.001,
                "lock_days": 0,
                "maturity_date": None,
                "total_interest_earned": 0,
                "last_interest_at": datetime.now(UTC),
                "created_at": datetime.now(UTC),
            },
        ]

        resp = client.post(
            "/api/market/savings/deposit",
            json={"amount": 100, "account_type": "regular"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["amount"] == 100
        assert data["type_label"] == "普通預金"

    def test_deposit_insufficient(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.side_effect = [None]

        resp = client.post(
            "/api/market/savings/deposit",
            json={"amount": 100, "account_type": "regular"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_deposit_below_minimum(self, client, auth_headers, mock_pool):
        resp = client.post(
            "/api/market/savings/deposit",
            json={"amount": 5, "account_type": "regular"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_withdraw(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": 1,
            "user_id": 123456789,
            "account_type": "regular",
            "balance": 500,
            "interest_rate": 0.001,
            "lock_days": 0,
            "maturity_date": None,
            "total_interest_earned": 10,
            "last_interest_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        }
        conn.execute.return_value = None

        resp = client.post(
            "/api/market/savings/withdraw",
            json={"amount": 200, "account_type": "regular"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["amount"] == 200
        assert data["new_balance"] == 300

    def test_interest_history(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "account_type": "regular",
                "amount": 5,
                "balance_after": 505,
                "calculated_at": datetime.now(UTC),
            },
        ]

        resp = client.get("/api/market/savings/interest-history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["amount"] == 5


class TestFleaMarket:
    def test_get_listings(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchval.return_value = 1
        conn.fetch.return_value = [
            {
                "id": 1,
                "seller_id": 999,
                "item_id": 10,
                "quantity": 2,
                "price_per_unit": 50,
                "status": "active",
                "expires_at": datetime.now(UTC) + timedelta(days=3),
                "created_at": datetime.now(UTC),
                "name": "テスト",
                "emoji": "🎁",
                "rarity": "common",
                "seller_name": "Seller",
            },
        ]

        resp = client.get("/api/market/flea/listings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_create_listing(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.side_effect = [
            {"quantity": 5},  # inv check
            {
                "id": 1,
                "seller_id": 123456789,
                "item_id": 10,
                "quantity": 2,
                "price_per_unit": 50,
                "status": "active",
                "expires_at": datetime.now(UTC) + timedelta(days=7),
                "created_at": datetime.now(UTC),
            },
            {"name": "テスト", "emoji": "🎁", "rarity": "common"},  # item details
        ]
        conn.execute.return_value = None

        resp = client.post(
            "/api/market/flea/listings",
            json={"item_id": 10, "quantity": 2, "price_per_unit": 50},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["quantity"] == 2
        assert data["price_per_unit"] == 50

    def test_create_listing_no_item(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.post(
            "/api/market/flea/listings",
            json={"item_id": 999, "quantity": 1, "price_per_unit": 50},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_buy_listing(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.side_effect = [
            # FOR UPDATE listing
            {
                "id": 1,
                "seller_id": 999,
                "item_id": 10,
                "quantity": 1,
                "price_per_unit": 100,
                "status": "active",
                "expires_at": datetime.now(UTC) + timedelta(days=3),
                "created_at": datetime.now(UTC),
            },
            # Spend
            {"balance": 895},
            # Item info
            {"name": "テスト", "emoji": "🎁"},
        ]
        conn.execute.return_value = None

        resp = client.post(
            "/api/market/flea/listings/1/buy",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 100
        assert data["fee"] == 5

    def test_buy_own_listing(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": 1,
            "seller_id": 123456789,
            "item_id": 10,
            "quantity": 1,
            "price_per_unit": 100,
            "status": "active",
            "expires_at": datetime.now(UTC) + timedelta(days=3),
            "created_at": datetime.now(UTC),
        }

        resp = client.post(
            "/api/market/flea/listings/1/buy",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_cancel_listing(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": 1,
            "seller_id": 123456789,
            "item_id": 10,
            "quantity": 1,
            "price_per_unit": 100,
            "status": "active",
            "expires_at": datetime.now(UTC) + timedelta(days=3),
            "created_at": datetime.now(UTC),
        }
        conn.execute.return_value = None

        resp = client.delete(
            "/api/market/flea/listings/1",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"

    def test_get_my_listings(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "seller_id": 123456789,
                "item_id": 10,
                "quantity": 1,
                "price_per_unit": 100,
                "status": "active",
                "expires_at": datetime.now(UTC) + timedelta(days=3),
                "created_at": datetime.now(UTC),
                "name": "テスト",
                "emoji": "🎁",
                "rarity": "common",
            },
        ]

        resp = client.get("/api/market/flea/my-listings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_get_item_price_history(self, client, auth_headers, mock_pool):
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "item_id": 10,
                "avg_price": 50,
                "min_price": 40,
                "max_price": 60,
                "volume": 5,
                "recorded_date": datetime.now(UTC).date(),
            },
        ]

        resp = client.get(
            "/api/market/flea/items/10/price-history",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["avg_price"] == 50

    def test_no_auth(self, client, mock_pool):
        resp = client.get("/api/market/stocks")
        assert resp.status_code in (401, 403)
