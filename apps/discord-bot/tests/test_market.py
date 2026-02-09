"""MarketManager テスト — 株式市場・貯金銀行・フリーマーケット"""

import math
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from studybot.managers.market_manager import MarketManager

from tests.conftest import MockAsyncContextManager


@pytest.fixture
def mock_db_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value = MockAsyncContextManager(conn)
    conn.transaction = MagicMock(return_value=MockAsyncContextManager(conn))
    return pool, conn


@pytest.fixture
def market_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = MarketManager(pool)
    return manager, conn


# ===== 株式市場テスト =====


class TestStockMarket:
    @pytest.mark.asyncio
    async def test_get_all_stocks(self, market_manager):
        manager, conn = market_manager
        conn.fetch.return_value = [
            {
                "id": 1, "symbol": "MATH", "name": "数学株",
                "topic_keyword": "数学", "description": "", "emoji": "📐",
                "sector": "理系", "base_price": 100, "current_price": 110,
                "previous_close": 100, "total_shares": 10000,
                "circulating_shares": 50, "active": True,
                "listed_at": datetime.now(UTC), "updated_at": datetime.now(UTC),
            },
        ]

        stocks = await manager.get_all_stocks()
        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "MATH"
        assert stocks[0]["change_pct"] == 10.0

    @pytest.mark.asyncio
    async def test_get_stock_detail(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.return_value = {
            "id": 1, "symbol": "CODE", "name": "プログラミング株",
            "topic_keyword": "プログラミング", "description": "テスト",
            "emoji": "💻", "sector": "技術", "base_price": 100,
            "current_price": 120, "previous_close": 100,
            "total_shares": 10000, "circulating_shares": 100, "active": True,
            "listed_at": datetime.now(UTC), "updated_at": datetime.now(UTC),
        }
        conn.fetch.return_value = []

        detail = await manager.get_stock_detail("CODE")
        assert detail is not None
        assert detail["symbol"] == "CODE"
        assert detail["change_pct"] == 20.0

    @pytest.mark.asyncio
    async def test_get_stock_detail_not_found(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.return_value = None

        detail = await manager.get_stock_detail("INVALID")
        assert detail is None

    @pytest.mark.asyncio
    async def test_buy_stock_success(self, market_manager):
        manager, conn = market_manager
        # get_stock_by_symbol
        conn.fetchrow.side_effect = [
            {
                "id": 1, "symbol": "MATH", "name": "数学株",
                "topic_keyword": "数学", "description": "", "emoji": "📐",
                "sector": "理系", "base_price": 100, "current_price": 100,
                "previous_close": 100, "total_shares": 10000,
                "circulating_shares": 0, "active": True,
                "listed_at": datetime.now(UTC), "updated_at": datetime.now(UTC),
            },
            # spend coins (balance check)
            {"balance": 900},
            # existing holding check
            None,
        ]
        conn.execute.return_value = None

        result = await manager.buy_stock(123, "MATH", 1)
        assert "error" not in result
        assert result["shares"] == 1
        assert result["total"] == 100
        assert result["balance"] == 900

    @pytest.mark.asyncio
    async def test_buy_stock_invalid_shares(self, market_manager):
        manager, conn = market_manager
        result = await manager.buy_stock(123, "MATH", 0)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_buy_stock_exceeds_max(self, market_manager):
        manager, conn = market_manager
        result = await manager.buy_stock(123, "MATH", 200)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_buy_stock_not_found(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.return_value = None
        result = await manager.buy_stock(123, "INVALID", 1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_buy_stock_insufficient_coins(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.side_effect = [
            {
                "id": 1, "symbol": "MATH", "name": "数学株",
                "topic_keyword": "数学", "description": "", "emoji": "📐",
                "sector": "理系", "base_price": 100, "current_price": 100,
                "previous_close": 100, "total_shares": 10000,
                "circulating_shares": 0, "active": True,
                "listed_at": datetime.now(UTC), "updated_at": datetime.now(UTC),
            },
            # spend coins - fails (balance < needed)
            None,
        ]

        result = await manager.buy_stock(123, "MATH", 1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_sell_stock_success(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.side_effect = [
            # get_stock_by_symbol
            {
                "id": 1, "symbol": "MATH", "name": "数学株",
                "topic_keyword": "数学", "description": "", "emoji": "📐",
                "sector": "理系", "base_price": 100, "current_price": 120,
                "previous_close": 100, "total_shares": 10000,
                "circulating_shares": 10, "active": True,
                "listed_at": datetime.now(UTC), "updated_at": datetime.now(UTC),
            },
            # holding check
            {"shares": 5, "avg_buy_price": 100, "total_invested": 500},
            # balance after sell
            {"balance": 1120},
        ]
        conn.execute.return_value = None

        result = await manager.sell_stock(123, "MATH", 2)
        assert "error" not in result
        assert result["shares"] == 2
        assert result["total"] == 240
        assert result["profit"] == 40

    @pytest.mark.asyncio
    async def test_sell_stock_insufficient_holdings(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.side_effect = [
            {
                "id": 1, "symbol": "MATH", "name": "数学株",
                "topic_keyword": "数学", "description": "", "emoji": "📐",
                "sector": "理系", "base_price": 100, "current_price": 120,
                "previous_close": 100, "total_shares": 10000,
                "circulating_shares": 10, "active": True,
                "listed_at": datetime.now(UTC), "updated_at": datetime.now(UTC),
            },
            None,  # no holding found
        ]

        result = await manager.sell_stock(123, "MATH", 5)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_portfolio_empty(self, market_manager):
        manager, conn = market_manager
        conn.fetch.return_value = []

        portfolio = await manager.get_portfolio(123)
        assert portfolio["holdings"] == []
        assert portfolio["total_value"] == 0

    @pytest.mark.asyncio
    async def test_get_portfolio_with_holdings(self, market_manager):
        manager, conn = market_manager
        conn.fetch.return_value = [
            {
                "id": 1, "user_id": 123, "stock_id": 1, "shares": 10,
                "avg_buy_price": 100, "total_invested": 1000,
                "symbol": "MATH", "name": "数学株", "emoji": "📐",
                "current_price": 120, "sector": "理系",
                "updated_at": datetime.now(UTC),
            },
        ]

        portfolio = await manager.get_portfolio(123)
        assert len(portfolio["holdings"]) == 1
        h = portfolio["holdings"][0]
        assert h["market_value"] == 1200
        assert h["profit"] == 200
        assert h["profit_pct"] == 20.0
        assert portfolio["total_value"] == 1200

    @pytest.mark.asyncio
    async def test_get_transactions(self, market_manager):
        manager, conn = market_manager
        conn.fetch.return_value = [
            {
                "id": 1, "user_id": 123, "stock_id": 1,
                "transaction_type": "buy", "shares": 5,
                "price_per_share": 100, "total_amount": 500,
                "created_at": datetime.now(UTC),
                "symbol": "MATH", "name": "数学株", "emoji": "📐",
            }
        ]
        conn.fetchval.return_value = 1

        data = await manager.get_transactions(123)
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_price_algorithm_trend_up(self, market_manager):
        manager, conn = market_manager
        stock = {
            "id": 1, "symbol": "MATH", "topic_keyword": "数学",
            "base_price": 100, "current_price": 100, "previous_close": 100,
        }
        # this week = 200 min, last week = 100 min → trend = 201/101 ≈ 1.99
        conn.fetchval.side_effect = [200, 100, 0]

        new_price = await manager._calculate_new_price(stock, datetime.now(UTC))
        assert new_price > 100  # should increase

    @pytest.mark.asyncio
    async def test_price_algorithm_trend_down(self, market_manager):
        manager, conn = market_manager
        stock = {
            "id": 1, "symbol": "MATH", "topic_keyword": "数学",
            "base_price": 100, "current_price": 100, "previous_close": 100,
        }
        # this week = 10 min, last week = 200 min → trend = 11/201 ≈ 0.055
        conn.fetchval.side_effect = [10, 200, 0]

        new_price = await manager._calculate_new_price(stock, datetime.now(UTC))
        assert new_price < 100  # should decrease

    @pytest.mark.asyncio
    async def test_price_algorithm_circuit_breaker(self, market_manager):
        manager, conn = market_manager
        stock = {
            "id": 1, "symbol": "MATH", "topic_keyword": "数学",
            "base_price": 100, "current_price": 100, "previous_close": 100,
        }
        # Extreme trend: this week = 1000, last week = 1
        conn.fetchval.side_effect = [1000, 1, 0]

        new_price = await manager._calculate_new_price(stock, datetime.now(UTC))
        # Circuit breaker: ±15% of previous_close (100) → max 115
        assert new_price <= 115

    @pytest.mark.asyncio
    async def test_price_algorithm_floor(self, market_manager):
        manager, conn = market_manager
        stock = {
            "id": 1, "symbol": "MATH", "topic_keyword": "数学",
            "base_price": 100, "current_price": 12, "previous_close": 12,
        }
        # Near floor: tiny activity
        conn.fetchval.side_effect = [0, 0, -100]

        new_price = await manager._calculate_new_price(stock, datetime.now(UTC))
        assert new_price >= 10  # min_price floor

    @pytest.mark.asyncio
    async def test_price_algorithm_ceiling(self, market_manager):
        manager, conn = market_manager
        stock = {
            "id": 1, "symbol": "MATH", "topic_keyword": "数学",
            "base_price": 9000, "current_price": 9900, "previous_close": 9900,
        }
        conn.fetchval.side_effect = [10000, 1, 1000]

        new_price = await manager._calculate_new_price(stock, datetime.now(UTC))
        assert new_price <= 10000  # max_price ceiling


# ===== 貯金銀行テスト =====


class TestSavingsBank:
    @pytest.mark.asyncio
    async def test_get_savings_status_empty(self, market_manager):
        manager, conn = market_manager
        conn.fetch.return_value = []

        status = await manager.get_savings_status(123)
        assert status["accounts"] == []
        assert status["total_savings"] == 0

    @pytest.mark.asyncio
    async def test_deposit_regular(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.side_effect = [
            {"balance": 900},  # spend coins
            {
                "id": 1, "user_id": 123, "account_type": "regular",
                "balance": 100, "interest_rate": 0.001,
                "lock_days": 0, "maturity_date": None,
                "total_interest_earned": 0, "last_interest_at": None,
                "created_at": datetime.now(UTC),
            },
        ]

        result = await manager.deposit(123, 100, "regular")
        assert "error" not in result
        assert result["amount"] == 100
        assert result["type_label"] == "普通預金"

    @pytest.mark.asyncio
    async def test_deposit_fixed(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.side_effect = [
            {"balance": 500},
            {
                "id": 2, "user_id": 123, "account_type": "fixed",
                "balance": 500, "interest_rate": 0.003,
                "lock_days": 7, "maturity_date": datetime.now(UTC) + timedelta(days=7),
                "total_interest_earned": 0, "last_interest_at": None,
                "created_at": datetime.now(UTC),
            },
        ]

        result = await manager.deposit(123, 500, "fixed")
        assert "error" not in result
        assert result["lock_days"] == 7

    @pytest.mark.asyncio
    async def test_deposit_below_minimum(self, market_manager):
        manager, conn = market_manager
        result = await manager.deposit(123, 5, "regular")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_deposit_invalid_type(self, market_manager):
        manager, conn = market_manager
        result = await manager.deposit(123, 100, "invalid")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_deposit_insufficient_coins(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.side_effect = [None]  # spend fails
        result = await manager.deposit(123, 100, "regular")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_withdraw_regular(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.side_effect = [
            {
                "id": 1, "user_id": 123, "account_type": "regular",
                "balance": 500, "interest_rate": 0.001,
                "lock_days": 0, "maturity_date": None,
                "total_interest_earned": 5, "last_interest_at": datetime.now(UTC),
                "created_at": datetime.now(UTC),
            },
        ]
        conn.execute.return_value = None

        result = await manager.withdraw(123, 200, "regular")
        assert "error" not in result
        assert result["amount"] == 200

    @pytest.mark.asyncio
    async def test_withdraw_fixed_before_maturity(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.return_value = {
            "id": 2, "user_id": 123, "account_type": "fixed",
            "balance": 500, "interest_rate": 0.003,
            "lock_days": 7, "maturity_date": datetime.now(UTC) + timedelta(days=5),
            "total_interest_earned": 0, "last_interest_at": None,
            "created_at": datetime.now(UTC),
        }

        result = await manager.withdraw(123, 100, "fixed")
        assert "error" in result
        assert "満期" in result["error"]

    @pytest.mark.asyncio
    async def test_withdraw_zero(self, market_manager):
        manager, conn = market_manager
        result = await manager.withdraw(123, 0, "regular")
        assert "error" in result


# ===== フリーマーケットテスト =====


class TestFleaMarket:
    @pytest.mark.asyncio
    async def test_create_listing_success(self, market_manager):
        manager, conn = market_manager
        conn.fetch.return_value = []  # user_listings (empty = under limit)
        conn.fetchrow.side_effect = [
            {"quantity": 5},  # inv check
            {
                "id": 1, "seller_id": 123, "item_id": 10,
                "quantity": 2, "price_per_unit": 50,
                "status": "active",
                "expires_at": datetime.now(UTC) + timedelta(days=7),
                "created_at": datetime.now(UTC),
            },
        ]
        conn.execute.return_value = None

        result = await manager.create_listing(123, 10, 2, 50)
        assert "error" not in result
        assert result["listing_id"] == 1

    @pytest.mark.asyncio
    async def test_create_listing_price_too_low(self, market_manager):
        manager, conn = market_manager
        result = await manager.create_listing(123, 10, 1, 0)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_listing_price_too_high(self, market_manager):
        manager, conn = market_manager
        result = await manager.create_listing(123, 10, 1, 200000)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_listing_zero_quantity(self, market_manager):
        manager, conn = market_manager
        result = await manager.create_listing(123, 10, 0, 50)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_buy_listing_success(self, market_manager):
        manager, conn = market_manager
        # get_listing
        conn.fetchrow.side_effect = [
            {
                "id": 1, "seller_id": 999, "item_id": 10,
                "quantity": 1, "price_per_unit": 100,
                "status": "active", "name": "テストアイテム",
                "emoji": "🎁", "rarity": "common",
                "seller_name": "Seller",
                "expires_at": datetime.now(UTC) + timedelta(days=3),
                "created_at": datetime.now(UTC),
            },
            # buy_listing result in repository
            None,  # FOR UPDATE
            {"balance": 895},  # spend
        ]
        conn.execute.return_value = None

        # Mock the repository directly
        manager.repository.buy_listing = AsyncMock(return_value={
            "listing_id": 1, "item_id": 10, "quantity": 1,
            "total": 100, "fee": 5, "balance": 895,
        })

        result = await manager.buy_listing(123, 1)
        assert "error" not in result
        assert result["total"] == 100
        assert result["fee"] == 5

    @pytest.mark.asyncio
    async def test_buy_listing_not_found(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.return_value = None

        result = await manager.buy_listing(123, 999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_buy_listing_own_item(self, market_manager):
        manager, conn = market_manager
        conn.fetchrow.return_value = {
            "id": 1, "seller_id": 123, "item_id": 10,
            "quantity": 1, "price_per_unit": 100,
            "status": "active", "name": "Test", "emoji": "🎁",
            "rarity": "common", "seller_name": "Self",
            "expires_at": datetime.now(UTC) + timedelta(days=3),
            "created_at": datetime.now(UTC),
        }

        result = await manager.buy_listing(123, 1)
        assert "error" in result
        assert "自分" in result["error"]

    @pytest.mark.asyncio
    async def test_cancel_listing_success(self, market_manager):
        manager, conn = market_manager
        manager.repository.cancel_listing = AsyncMock(return_value=True)

        result = await manager.cancel_listing(123, 1)
        assert result["cancelled"] is True

    @pytest.mark.asyncio
    async def test_cancel_listing_not_found(self, market_manager):
        manager, conn = market_manager
        manager.repository.cancel_listing = AsyncMock(return_value=False)

        result = await manager.cancel_listing(123, 999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_listings(self, market_manager):
        manager, conn = market_manager
        conn.fetch.return_value = [
            {
                "id": 1, "seller_id": 999, "item_id": 10,
                "quantity": 1, "price_per_unit": 100,
                "status": "active", "name": "Test",
                "emoji": "🎁", "rarity": "common",
                "seller_name": "Seller",
                "expires_at": datetime.now(UTC) + timedelta(days=3),
                "created_at": datetime.now(UTC),
            },
        ]
        conn.fetchval.return_value = 1

        data = await manager.get_listings()
        assert data["total"] == 1
        assert len(data["items"]) == 1
