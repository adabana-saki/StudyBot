"""ショップ・通貨のテスト"""

import pytest

from studybot.managers.currency_manager import CurrencyManager


@pytest.fixture
def currency_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = CurrencyManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_get_balance(currency_manager):
    """残高取得テスト"""
    manager, conn = currency_manager

    conn.fetchval.return_value = 500

    balance = await manager.get_balance(123)
    assert balance == 500


@pytest.mark.asyncio
async def test_get_balance_no_record(currency_manager):
    """残高レコードなしの場合は0"""
    manager, conn = currency_manager

    conn.fetchval.return_value = None

    balance = await manager.get_balance(123)
    assert balance == 0


@pytest.mark.asyncio
async def test_award_coins(currency_manager):
    """コイン付与テスト"""
    manager, conn = currency_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        # ensure_currency -> INSERT returns row
        {
            "user_id": 123,
            "balance": 0,
            "total_earned": 0,
            "total_spent": 0,
            "updated_at": None,
        },
        # add_coins -> UPDATE returns row
        {
            "user_id": 123,
            "balance": 50,
            "total_earned": 50,
            "total_spent": 0,
            "updated_at": None,
        },
    ]

    result = await manager.award_coins(123, "TestUser", 50, "ポモドーロ完了")
    assert result["amount"] == 50
    assert result["balance"] == 50
    assert result["total_earned"] == 50
    assert "error" not in result


@pytest.mark.asyncio
async def test_award_coins_existing_user(currency_manager):
    """既存ユーザーへのコイン付与"""
    manager, conn = currency_manager

    conn.execute.return_value = None  # ensure_user
    conn.fetchrow.side_effect = [
        # ensure_currency -> INSERT ON CONFLICT returns None, then SELECT
        None,
        {
            "user_id": 123,
            "balance": 100,
            "total_earned": 200,
            "total_spent": 100,
            "updated_at": None,
        },
        # add_coins -> UPDATE returns row
        {
            "user_id": 123,
            "balance": 110,
            "total_earned": 210,
            "total_spent": 100,
            "updated_at": None,
        },
    ]

    result = await manager.award_coins(123, "TestUser", 10, "学習ログ")
    assert result["amount"] == 10
    assert result["balance"] == 110


@pytest.mark.asyncio
async def test_purchase_success(currency_manager):
    """購入成功テスト"""
    manager, conn = currency_manager

    # get_item
    conn.fetchrow.side_effect = [
        {
            "id": 1,
            "name": "テストアイテム",
            "description": "テスト用",
            "category": "cosmetic",
            "price": 100,
            "rarity": "common",
            "emoji": "🎁",
            "metadata": {},
            "active": True,
        },
    ]
    # get_balance
    conn.fetchval.side_effect = [
        200,  # balance check
        150,  # new balance after purchase
    ]
    # purchase_item transaction
    conn.execute.return_value = None
    # purchase_item: spend_coins returns a row (success)
    item_fetchrow = {
        "user_id": 123,
    }

    # Reset side_effect for the transaction calls
    conn.fetchrow.side_effect = [
        # get_item
        {
            "id": 1,
            "name": "テストアイテム",
            "description": "テスト用",
            "category": "cosmetic",
            "price": 100,
            "rarity": "common",
            "emoji": "🎁",
            "metadata": {},
            "active": True,
        },
        # purchase_item -> spend_coins returns row
        item_fetchrow,
    ]
    conn.fetchval.side_effect = [
        200,  # get_balance for check
        100,  # get_balance after purchase
    ]

    result = await manager.purchase(123, 1)
    assert "error" not in result
    assert result["item"]["name"] == "テストアイテム"
    assert result["price"] == 100
    assert result["balance"] == 100


@pytest.mark.asyncio
async def test_purchase_insufficient_funds(currency_manager):
    """残高不足での購入テスト"""
    manager, conn = currency_manager

    conn.fetchrow.side_effect = [
        # get_item
        {
            "id": 1,
            "name": "高級アイテム",
            "description": "テスト用",
            "category": "cosmetic",
            "price": 1000,
            "rarity": "epic",
            "emoji": "💎",
            "metadata": {},
            "active": True,
        },
    ]
    conn.fetchval.return_value = 50  # balance = 50 < price = 1000

    result = await manager.purchase(123, 1)
    assert "error" in result
    assert result["error"] == "コインが足りません"
    assert result["balance"] == 50
    assert result["price"] == 1000


@pytest.mark.asyncio
async def test_purchase_item_not_found(currency_manager):
    """存在しないアイテムの購入テスト"""
    manager, conn = currency_manager

    conn.fetchrow.return_value = None  # get_item returns None

    result = await manager.purchase(123, 999)
    assert "error" in result
    assert result["error"] == "アイテムが見つかりません"


@pytest.mark.asyncio
async def test_get_shop_page(currency_manager):
    """ショップページネーションテスト"""
    manager, conn = currency_manager

    # 8件のアイテム（5件/ページ）
    items = [
        {
            "id": i,
            "name": f"アイテム{i}",
            "description": f"説明{i}",
            "category": "cosmetic",
            "price": i * 100,
            "rarity": "common",
            "emoji": "🎁",
            "metadata": {},
            "active": True,
        }
        for i in range(1, 9)
    ]

    conn.fetch.return_value = items

    result = await manager.get_shop_page(page=0, per_page=5)
    assert result["page"] == 0
    assert result["total_pages"] == 2
    assert result["total_items"] == 8
    assert len(result["items"]) == 5

    # 2ページ目
    conn.fetch.return_value = items
    result = await manager.get_shop_page(page=1, per_page=5)
    assert result["page"] == 1
    assert len(result["items"]) == 3


@pytest.mark.asyncio
async def test_get_shop_page_empty(currency_manager):
    """空ショップのページネーション"""
    manager, conn = currency_manager

    conn.fetch.return_value = []

    result = await manager.get_shop_page(page=0)
    assert result["page"] == 0
    assert result["total_pages"] == 1
    assert result["total_items"] == 0
    assert len(result["items"]) == 0


@pytest.mark.asyncio
async def test_get_inventory(currency_manager):
    """インベントリ取得テスト"""
    manager, conn = currency_manager

    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123,
            "item_id": 1,
            "quantity": 2,
            "equipped": False,
            "acquired_at": None,
            "name": "テストアイテム",
            "description": "テスト",
            "category": "cosmetic",
            "price": 100,
            "rarity": "common",
            "emoji": "🎁",
        }
    ]

    inventory = await manager.get_inventory(123)
    assert len(inventory) == 1
    assert inventory[0]["name"] == "テストアイテム"
    assert inventory[0]["quantity"] == 2
