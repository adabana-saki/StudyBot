"""通貨・ショップ ビジネスロジック"""

import logging

from studybot.repositories.currency_repository import CurrencyRepository

logger = logging.getLogger(__name__)


class CurrencyManager:
    """StudyCoin・ショップの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = CurrencyRepository(db_pool)

    async def get_balance(self, user_id: int) -> int:
        """残高を取得"""
        return await self.repository.get_balance(user_id)

    async def award_coins(self, user_id: int, username: str, amount: int, reason: str) -> dict:
        """コインを付与（ユーザー初期化込み）"""
        await self.repository.ensure_user(user_id, username)
        await self.repository.ensure_currency(user_id)
        result = await self.repository.add_coins(user_id, amount, reason)
        if not result:
            return {"error": "コイン付与に失敗しました"}

        return {
            "amount": amount,
            "reason": reason,
            "balance": result["balance"],
            "total_earned": result["total_earned"],
        }

    async def purchase(self, user_id: int, item_id: int) -> dict:
        """アイテムを購入"""
        # アイテム存在チェック
        item = await self.repository.get_item(item_id)
        if not item:
            return {"error": "アイテムが見つかりません"}

        # 残高チェック
        balance = await self.repository.get_balance(user_id)
        if balance < item["price"]:
            return {
                "error": "コインが足りません",
                "balance": balance,
                "price": item["price"],
            }

        # 購入実行
        success = await self.repository.purchase_item(user_id, item_id, item["price"])
        if not success:
            return {"error": "購入処理に失敗しました"}

        new_balance = await self.repository.get_balance(user_id)
        return {
            "item": item,
            "price": item["price"],
            "balance": new_balance,
        }

    async def get_shop_page(self, category=None, page: int = 0, per_page: int = 5) -> dict:
        """ページネーション付きショップアイテムを取得"""
        items = await self.repository.get_shop_items(category=category)
        total = len(items)
        total_pages = max(1, (total + per_page - 1) // per_page)

        # ページ範囲の正規化
        page = max(0, min(page, total_pages - 1))

        start = page * per_page
        end = start + per_page
        page_items = items[start:end]

        return {
            "items": page_items,
            "page": page,
            "total_pages": total_pages,
            "total_items": total,
        }

    async def get_inventory(self, user_id: int) -> list[dict]:
        """ユーザーのインベントリを取得"""
        return await self.repository.get_inventory(user_id)

    async def equip_item(self, user_id: int, item_id: int) -> dict:
        """アイテムを装備"""
        inventory = await self.repository.get_inventory(user_id)
        owned = [i for i in inventory if i["item_id"] == item_id]
        if not owned:
            return {"error": "このアイテムを持っていません。"}

        item = owned[0]
        await self.repository.equip_item(user_id, item_id)
        return {"item": item}

    async def get_user_preferences(self, user_id: int) -> dict | None:
        """ユーザー設定を取得"""
        return await self.repository.get_user_preferences(user_id)

    async def update_user_preferences(self, user_id: int, **kwargs) -> dict:
        """ユーザー設定を更新"""
        return await self.repository.update_user_preferences(user_id, **kwargs)
