"""通貨・ショップ DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CurrencyRepository(BaseRepository):
    """StudyCoin・ショップ関連のCRUD"""

    async def get_balance(self, user_id: int) -> int:
        """ユーザーの残高を取得"""
        async with self.db_pool.acquire() as conn:
            balance = await conn.fetchval(
                "SELECT balance FROM virtual_currency WHERE user_id = $1",
                user_id,
            )
        return balance or 0

    async def ensure_currency(self, user_id: int) -> dict:
        """通貨レコードを確保（なければ作成）"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO virtual_currency (user_id, balance, total_earned, total_spent)
                VALUES ($1, 0, 0, 0)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING *
                """,
                user_id,
            )
            if not row:
                row = await conn.fetchrow(
                    "SELECT * FROM virtual_currency WHERE user_id = $1",
                    user_id,
                )
        return dict(row)

    async def add_coins(self, user_id: int, amount: int, reason: str) -> dict:
        """コインを付与し、新しい残高を返す"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE virtual_currency
                SET balance = balance + $2,
                    total_earned = total_earned + $2,
                    updated_at = $3
                WHERE user_id = $1
                RETURNING *
                """,
                user_id,
                amount,
                datetime.now(UTC),
            )
        return dict(row) if row else {}

    async def spend_coins(self, user_id: int, amount: int) -> bool:
        """コインを消費（残高不足の場合はFalse）"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE virtual_currency
                SET balance = balance - $2,
                    total_spent = total_spent + $2,
                    updated_at = $3
                WHERE user_id = $1 AND balance >= $2
                RETURNING user_id
                """,
                user_id,
                amount,
                datetime.now(UTC),
            )
        return row is not None

    async def get_shop_items(self, category=None, active: bool = True) -> list[dict]:
        """ショップアイテム一覧を取得"""
        query = "SELECT * FROM shop_items WHERE active = $1"
        params: list = [active]

        if category:
            query += " AND category = $2"
            params.append(category)

        query += " ORDER BY category, price"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    async def get_item(self, item_id: int) -> dict | None:
        """アイテム情報を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM shop_items WHERE id = $1 AND active = true",
                item_id,
            )
        return dict(row) if row else None

    async def get_inventory(self, user_id: int) -> list[dict]:
        """ユーザーのインベントリを取得（アイテム情報付き）"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ui.id, ui.user_id, ui.item_id, ui.quantity, ui.equipped,
                       ui.acquired_at, si.name, si.description, si.category,
                       si.price, si.rarity, si.emoji
                FROM user_inventory ui
                JOIN shop_items si ON si.id = ui.item_id
                WHERE ui.user_id = $1
                ORDER BY ui.acquired_at DESC
                """,
                user_id,
            )
        return [dict(row) for row in rows]

    async def purchase_item(self, user_id: int, item_id: int, price: int) -> bool:
        """アイテムを購入（トランザクション）"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 残高チェック＆消費
                spent = await conn.fetchrow(
                    """
                    UPDATE virtual_currency
                    SET balance = balance - $2,
                        total_spent = total_spent + $2,
                        updated_at = $3
                    WHERE user_id = $1 AND balance >= $2
                    RETURNING user_id
                    """,
                    user_id,
                    price,
                    datetime.now(UTC),
                )
                if not spent:
                    return False

                # インベントリに追加（既存なら数量増加）
                await conn.execute(
                    """
                    INSERT INTO user_inventory (user_id, item_id, quantity, acquired_at)
                    VALUES ($1, $2, 1, $3)
                    ON CONFLICT (user_id, item_id)
                    DO UPDATE SET quantity = user_inventory.quantity + 1
                    """,
                    user_id,
                    item_id,
                    datetime.now(UTC),
                )

                # 購入履歴を記録
                await conn.execute(
                    """
                    INSERT INTO purchase_history (user_id, item_id, price, purchased_at)
                    VALUES ($1, $2, $3, $4)
                    """,
                    user_id,
                    item_id,
                    price,
                    datetime.now(UTC),
                )

        return True
