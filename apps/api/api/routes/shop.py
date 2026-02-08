"""ショップルート"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import CurrencyBalance, InventoryItem, PurchaseRequest, ShopItem

router = APIRouter(prefix="/api/shop", tags=["shop"])


@router.get("/items", response_model=list[ShopItem])
async def get_shop_items(
    category: str | None = None,
    page: int = 0,
    per_page: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """ショップアイテム一覧を取得"""
    pool = get_pool()
    async with pool.acquire() as conn:
        if category:
            rows = await conn.fetch(
                """
                SELECT * FROM shop_items
                WHERE active = true AND category = $1
                ORDER BY price
                LIMIT $2 OFFSET $3
                """,
                category,
                per_page,
                page * per_page,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM shop_items
                WHERE active = true
                ORDER BY category, price
                LIMIT $1 OFFSET $2
                """,
                per_page,
                page * per_page,
            )

    return [
        ShopItem(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            price=row["price"],
            rarity=row["rarity"],
            emoji=row["emoji"],
        )
        for row in rows
    ]


@router.get("/inventory", response_model=list[InventoryItem])
async def get_inventory(current_user: dict = Depends(get_current_user)):
    """インベントリを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ui.id, ui.item_id, ui.quantity, ui.equipped,
                   si.name, si.emoji, si.category
            FROM user_inventory ui
            JOIN shop_items si ON si.id = ui.item_id
            WHERE ui.user_id = $1
            ORDER BY ui.acquired_at DESC
            """,
            user_id,
        )

    return [
        InventoryItem(
            id=row["id"],
            item_id=row["item_id"],
            name=row["name"],
            emoji=row["emoji"],
            category=row["category"],
            quantity=row["quantity"],
            equipped=row["equipped"],
        )
        for row in rows
    ]


@router.post("/purchase")
async def purchase_item(
    request: PurchaseRequest,
    current_user: dict = Depends(get_current_user),
):
    """アイテムを購入"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        item = await conn.fetchrow(
            "SELECT * FROM shop_items WHERE id = $1 AND active = true",
            request.item_id,
        )
        if not item:
            raise HTTPException(status_code=404, detail="アイテムが見つかりません")

        async with conn.transaction():
            # SELECT FOR UPDATE で残高をロックして競合を防止
            balance = await conn.fetchval(
                "SELECT balance FROM virtual_currency WHERE user_id = $1 FOR UPDATE",
                user_id,
            )
            if (balance or 0) < item["price"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="コインが足りません",
                )

            new_balance = await conn.fetchval(
                """
                UPDATE virtual_currency
                SET balance = balance - $2, total_spent = total_spent + $2
                WHERE user_id = $1
                RETURNING balance
                """,
                user_id,
                item["price"],
            )
            await conn.execute(
                """
                INSERT INTO user_inventory (user_id, item_id, quantity)
                VALUES ($1, $2, 1)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = user_inventory.quantity + 1
                """,
                user_id,
                request.item_id,
            )
            await conn.execute(
                """
                INSERT INTO purchase_history (user_id, item_id, price)
                VALUES ($1, $2, $3)
                """,
                user_id,
                request.item_id,
                item["price"],
            )

    return {"message": "購入完了", "balance": new_balance}


@router.get("/balance", response_model=CurrencyBalance)
async def get_balance(current_user: dict = Depends(get_current_user)):
    """コイン残高を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT balance, total_earned, total_spent FROM virtual_currency WHERE user_id = $1",
            user_id,
        )

    if not row:
        return CurrencyBalance(balance=0, total_earned=0, total_spent=0)

    return CurrencyBalance(
        balance=row["balance"],
        total_earned=row["total_earned"],
        total_spent=row["total_spent"],
    )
