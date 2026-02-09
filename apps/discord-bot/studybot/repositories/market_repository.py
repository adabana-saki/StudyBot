"""投資市場 DB操作 — 株式・貯金・フリマ"""

import logging
import math
from datetime import UTC, datetime, timedelta

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MarketRepository(BaseRepository):
    """投資市場関連のCRUD"""

    # ===== 株式市場 =====

    async def get_all_stocks(self, active_only: bool = True) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            query = "SELECT * FROM study_stocks"
            if active_only:
                query += " WHERE active = true"
            query += " ORDER BY symbol"
            rows = await conn.fetch(query)
        return [dict(r) for r in rows]

    async def get_stock_by_symbol(self, symbol: str) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM study_stocks WHERE symbol = $1", symbol.upper()
            )
        return dict(row) if row else None

    async def get_stock_by_id(self, stock_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM study_stocks WHERE id = $1", stock_id
            )
        return dict(row) if row else None

    async def update_stock_price(
        self, stock_id: int, new_price: int, previous_close: int | None = None
    ) -> dict | None:
        async with self.db_pool.acquire() as conn:
            if previous_close is not None:
                row = await conn.fetchrow(
                    """
                    UPDATE study_stocks
                    SET current_price = $2, previous_close = $3, updated_at = $4
                    WHERE id = $1 RETURNING *
                    """,
                    stock_id, new_price, previous_close, datetime.now(UTC),
                )
            else:
                row = await conn.fetchrow(
                    """
                    UPDATE study_stocks
                    SET current_price = $2, updated_at = $3
                    WHERE id = $1 RETURNING *
                    """,
                    stock_id, new_price, datetime.now(UTC),
                )
        return dict(row) if row else None

    async def get_study_minutes_for_topic(
        self, topic_keyword: str, start: datetime, end: datetime
    ) -> int:
        """指定トピックの学習時間を集計"""
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT COALESCE(SUM(duration_minutes), 0)
                FROM study_logs
                WHERE LOWER(topic) LIKE '%' || LOWER($1) || '%'
                  AND logged_at >= $2 AND logged_at < $3
                """,
                topic_keyword, start, end,
            )
        return result or 0

    async def get_net_buy_volume(
        self, stock_id: int, since: datetime
    ) -> int:
        """直近の純買い越しボリュームを取得"""
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT COALESCE(
                    SUM(CASE WHEN transaction_type = 'buy' THEN shares
                             WHEN transaction_type = 'sell' THEN -shares
                             ELSE 0 END),
                    0
                )
                FROM stock_transactions
                WHERE stock_id = $1 AND created_at >= $2
                """,
                stock_id, since,
            )
        return result or 0

    async def save_price_snapshot(
        self, stock_id: int, price: int, volume: int,
        study_minutes: int, study_sessions: int, recorded_date
    ) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO stock_price_history
                    (stock_id, price, volume, study_minutes, study_sessions, recorded_date)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (stock_id, recorded_date) DO UPDATE SET
                    price = $2, volume = $3,
                    study_minutes = $4, study_sessions = $5
                """,
                stock_id, price, volume, study_minutes, study_sessions, recorded_date,
            )

    async def get_price_history(
        self, stock_id: int, days: int = 30
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM stock_price_history
                WHERE stock_id = $1
                  AND recorded_date >= CURRENT_DATE - $2::INT
                ORDER BY recorded_date
                """,
                stock_id, days,
            )
        return [dict(r) for r in rows]

    async def buy_stock(
        self, user_id: int, stock_id: int, shares: int, price_per_share: int
    ) -> dict | None:
        """株を購入 (トランザクション: コイン消費 + 保有追加 + 取引記録)"""
        total_cost = shares * price_per_share
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # コイン消費
                spent = await conn.fetchrow(
                    """
                    UPDATE virtual_currency
                    SET balance = balance - $2,
                        total_spent = total_spent + $2,
                        updated_at = $3
                    WHERE user_id = $1 AND balance >= $2
                    RETURNING balance
                    """,
                    user_id, total_cost, datetime.now(UTC),
                )
                if not spent:
                    return None

                # 保有株を更新
                existing = await conn.fetchrow(
                    "SELECT shares, avg_buy_price, total_invested FROM user_stock_holdings WHERE user_id = $1 AND stock_id = $2",
                    user_id, stock_id,
                )
                if existing:
                    old_shares = existing["shares"]
                    old_invested = existing["total_invested"]
                    new_shares = old_shares + shares
                    new_invested = old_invested + total_cost
                    new_avg = math.floor(new_invested / new_shares) if new_shares > 0 else 0
                    await conn.execute(
                        """
                        UPDATE user_stock_holdings
                        SET shares = $3, avg_buy_price = $4,
                            total_invested = $5, updated_at = $6
                        WHERE user_id = $1 AND stock_id = $2
                        """,
                        user_id, stock_id, new_shares, new_avg,
                        new_invested, datetime.now(UTC),
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO user_stock_holdings
                            (user_id, stock_id, shares, avg_buy_price, total_invested, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        user_id, stock_id, shares, price_per_share,
                        total_cost, datetime.now(UTC),
                    )

                # 流通株数を更新
                await conn.execute(
                    "UPDATE study_stocks SET circulating_shares = circulating_shares + $2 WHERE id = $1",
                    stock_id, shares,
                )

                # 取引記録
                await conn.execute(
                    """
                    INSERT INTO stock_transactions
                        (user_id, stock_id, transaction_type, shares, price_per_share, total_amount)
                    VALUES ($1, $2, 'buy', $3, $4, $5)
                    """,
                    user_id, stock_id, shares, price_per_share, total_cost,
                )

        return {"shares": shares, "price": price_per_share, "total": total_cost, "balance": spent["balance"]}

    async def sell_stock(
        self, user_id: int, stock_id: int, shares: int, price_per_share: int
    ) -> dict | None:
        """株を売却 (トランザクション: 保有減少 + コイン増加 + 取引記録)"""
        total_amount = shares * price_per_share
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 保有チェック & 減少
                holding = await conn.fetchrow(
                    """
                    SELECT shares, avg_buy_price, total_invested
                    FROM user_stock_holdings
                    WHERE user_id = $1 AND stock_id = $2 AND shares >= $3
                    """,
                    user_id, stock_id, shares,
                )
                if not holding:
                    return None

                new_shares = holding["shares"] - shares
                if new_shares == 0:
                    await conn.execute(
                        "DELETE FROM user_stock_holdings WHERE user_id = $1 AND stock_id = $2",
                        user_id, stock_id,
                    )
                else:
                    ratio = new_shares / holding["shares"]
                    new_invested = math.floor(holding["total_invested"] * ratio)
                    new_avg = math.floor(new_invested / new_shares) if new_shares > 0 else 0
                    await conn.execute(
                        """
                        UPDATE user_stock_holdings
                        SET shares = $3, avg_buy_price = $4,
                            total_invested = $5, updated_at = $6
                        WHERE user_id = $1 AND stock_id = $2
                        """,
                        user_id, stock_id, new_shares, new_avg,
                        new_invested, datetime.now(UTC),
                    )

                # 流通株数を更新
                await conn.execute(
                    "UPDATE study_stocks SET circulating_shares = GREATEST(circulating_shares - $2, 0) WHERE id = $1",
                    stock_id, shares,
                )

                # コイン加算
                balance_row = await conn.fetchrow(
                    """
                    UPDATE virtual_currency
                    SET balance = balance + $2,
                        total_earned = total_earned + $2,
                        updated_at = $3
                    WHERE user_id = $1
                    RETURNING balance
                    """,
                    user_id, total_amount, datetime.now(UTC),
                )

                # 取引記録
                await conn.execute(
                    """
                    INSERT INTO stock_transactions
                        (user_id, stock_id, transaction_type, shares, price_per_share, total_amount)
                    VALUES ($1, $2, 'sell', $3, $4, $5)
                    """,
                    user_id, stock_id, shares, price_per_share, total_amount,
                )

                # 損益計算
                profit = total_amount - (holding["avg_buy_price"] * shares)

        return {
            "shares": shares, "price": price_per_share,
            "total": total_amount, "profit": profit,
            "balance": balance_row["balance"] if balance_row else 0,
        }

    async def get_user_holdings(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT h.*, s.symbol, s.name, s.emoji, s.current_price, s.sector
                FROM user_stock_holdings h
                JOIN study_stocks s ON s.id = h.stock_id
                WHERE h.user_id = $1
                ORDER BY s.symbol
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def get_stock_transactions(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*, s.symbol, s.name, s.emoji
                FROM stock_transactions t
                JOIN study_stocks s ON s.id = t.stock_id
                WHERE t.user_id = $1
                ORDER BY t.created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset,
            )
        return [dict(r) for r in rows]

    async def get_stock_transaction_count(self, user_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM stock_transactions WHERE user_id = $1",
                user_id,
            )

    # ===== 貯金銀行 =====

    async def get_savings_accounts(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM savings_accounts WHERE user_id = $1 ORDER BY account_type",
                user_id,
            )
        return [dict(r) for r in rows]

    async def get_savings_account(
        self, user_id: int, account_type: str
    ) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM savings_accounts WHERE user_id = $1 AND account_type = $2",
                user_id, account_type,
            )
        return dict(row) if row else None

    async def deposit(
        self, user_id: int, account_type: str, amount: int,
        interest_rate: float, lock_days: int
    ) -> dict | None:
        """預金 (トランザクション: コイン消費 + 口座入金)"""
        now = datetime.now(UTC)
        maturity_date = now + timedelta(days=lock_days) if lock_days > 0 else None

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # コイン消費
                spent = await conn.fetchrow(
                    """
                    UPDATE virtual_currency
                    SET balance = balance - $2,
                        total_spent = total_spent + $2,
                        updated_at = $3
                    WHERE user_id = $1 AND balance >= $2
                    RETURNING balance
                    """,
                    user_id, amount, now,
                )
                if not spent:
                    return None

                # 口座に入金 (存在しなければ作成)
                row = await conn.fetchrow(
                    """
                    INSERT INTO savings_accounts
                        (user_id, account_type, balance, interest_rate,
                         lock_days, maturity_date, last_interest_at, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
                    ON CONFLICT (user_id, account_type) DO UPDATE SET
                        balance = savings_accounts.balance + $3,
                        maturity_date = CASE
                            WHEN $6 IS NOT NULL THEN $6
                            ELSE savings_accounts.maturity_date
                        END,
                        last_interest_at = COALESCE(savings_accounts.last_interest_at, $7)
                    RETURNING *
                    """,
                    user_id, account_type, amount, interest_rate,
                    lock_days, maturity_date, now,
                )
        return dict(row) if row else None

    async def withdraw(
        self, user_id: int, account_type: str, amount: int
    ) -> dict | None:
        """引き出し (トランザクション: 口座出金 + コイン加算)"""
        now = datetime.now(UTC)
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 口座チェック
                account = await conn.fetchrow(
                    "SELECT * FROM savings_accounts WHERE user_id = $1 AND account_type = $2 AND balance >= $3",
                    user_id, account_type, amount,
                )
                if not account:
                    return None

                # 定期預金: 満期前は引き出し不可
                if account_type == "fixed" and account["maturity_date"]:
                    if now < account["maturity_date"]:
                        return None

                # 口座から出金
                new_balance = account["balance"] - amount
                await conn.execute(
                    "UPDATE savings_accounts SET balance = $3 WHERE user_id = $1 AND account_type = $2",
                    user_id, account_type, new_balance,
                )

                # コイン加算
                await conn.execute(
                    """
                    UPDATE virtual_currency
                    SET balance = balance + $2,
                        total_earned = total_earned + $2,
                        updated_at = $3
                    WHERE user_id = $1
                    """,
                    user_id, amount, now,
                )

        return {"amount": amount, "new_balance": new_balance}

    async def calculate_and_apply_interest(self) -> list[dict]:
        """全口座の利息計算と適用 (日次バッチ)"""
        now = datetime.now(UTC)
        results = []
        async with self.db_pool.acquire() as conn:
            # 利息対象口座を取得
            accounts = await conn.fetch(
                """
                SELECT * FROM savings_accounts
                WHERE balance >= 100
                  AND (last_interest_at IS NULL
                       OR last_interest_at < CURRENT_DATE)
                """
            )
            for acc in accounts:
                # 定期預金は満期前は利息なし
                if acc["account_type"] == "fixed" and acc["maturity_date"]:
                    if now < acc["maturity_date"]:
                        continue

                interest = max(1, math.floor(acc["balance"] * acc["interest_rate"]))
                async with conn.transaction():
                    new_balance = acc["balance"] + interest
                    await conn.execute(
                        """
                        UPDATE savings_accounts
                        SET balance = $2,
                            total_interest_earned = total_interest_earned + $3,
                            last_interest_at = $4
                        WHERE id = $1
                        """,
                        acc["id"], new_balance, interest, now,
                    )
                    await conn.execute(
                        """
                        INSERT INTO interest_history (account_id, amount, balance_after, calculated_at)
                        VALUES ($1, $2, $3, $4)
                        """,
                        acc["id"], interest, new_balance, now,
                    )
                results.append({
                    "user_id": acc["user_id"],
                    "account_type": acc["account_type"],
                    "interest": interest,
                    "new_balance": new_balance,
                })
        return results

    async def get_interest_history(
        self, user_id: int, limit: int = 20
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ih.*, sa.account_type
                FROM interest_history ih
                JOIN savings_accounts sa ON sa.id = ih.account_id
                WHERE sa.user_id = $1
                ORDER BY ih.calculated_at DESC
                LIMIT $2
                """,
                user_id, limit,
            )
        return [dict(r) for r in rows]

    # ===== フリーマーケット =====

    async def create_listing(
        self, seller_id: int, item_id: int, quantity: int,
        price_per_unit: int, expires_at: datetime
    ) -> dict | None:
        """出品 (トランザクション: インベントリ消費 + 出品作成)"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # インベントリチェック & 消費
                inv = await conn.fetchrow(
                    "SELECT quantity FROM user_inventory WHERE user_id = $1 AND item_id = $2 AND quantity >= $3",
                    seller_id, item_id, quantity,
                )
                if not inv:
                    return None

                new_qty = inv["quantity"] - quantity
                if new_qty == 0:
                    await conn.execute(
                        "DELETE FROM user_inventory WHERE user_id = $1 AND item_id = $2",
                        seller_id, item_id,
                    )
                else:
                    await conn.execute(
                        "UPDATE user_inventory SET quantity = $3 WHERE user_id = $1 AND item_id = $2",
                        seller_id, item_id, new_qty,
                    )

                # 出品作成
                row = await conn.fetchrow(
                    """
                    INSERT INTO market_listings
                        (seller_id, item_id, quantity, price_per_unit, expires_at)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING *
                    """,
                    seller_id, item_id, quantity, price_per_unit, expires_at,
                )
        return dict(row) if row else None

    async def get_active_listings(
        self, item_id: int | None = None,
        limit: int = 20, offset: int = 0
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            if item_id:
                rows = await conn.fetch(
                    """
                    SELECT ml.*, si.name, si.emoji, si.rarity,
                           u.username AS seller_name
                    FROM market_listings ml
                    JOIN shop_items si ON si.id = ml.item_id
                    JOIN users u ON u.user_id = ml.seller_id
                    WHERE ml.status = 'active'
                      AND ml.expires_at > NOW()
                      AND ml.item_id = $1
                    ORDER BY ml.price_per_unit ASC
                    LIMIT $2 OFFSET $3
                    """,
                    item_id, limit, offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT ml.*, si.name, si.emoji, si.rarity,
                           u.username AS seller_name
                    FROM market_listings ml
                    JOIN shop_items si ON si.id = ml.item_id
                    JOIN users u ON u.user_id = ml.seller_id
                    WHERE ml.status = 'active'
                      AND ml.expires_at > NOW()
                    ORDER BY ml.created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit, offset,
                )
        return [dict(r) for r in rows]

    async def get_active_listing_count(self, item_id: int | None = None) -> int:
        async with self.db_pool.acquire() as conn:
            if item_id:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM market_listings WHERE status = 'active' AND expires_at > NOW() AND item_id = $1",
                    item_id,
                )
            return await conn.fetchval(
                "SELECT COUNT(*) FROM market_listings WHERE status = 'active' AND expires_at > NOW()"
            )

    async def get_listing(self, listing_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT ml.*, si.name, si.emoji, si.rarity,
                       u.username AS seller_name
                FROM market_listings ml
                JOIN shop_items si ON si.id = ml.item_id
                JOIN users u ON u.user_id = ml.seller_id
                WHERE ml.id = $1
                """,
                listing_id,
            )
        return dict(row) if row else None

    async def buy_listing(
        self, buyer_id: int, listing_id: int, fee_rate: float
    ) -> dict | None:
        """フリマ購入 (トランザクション)"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 出品情報取得 (FOR UPDATE でロック)
                listing = await conn.fetchrow(
                    """
                    SELECT * FROM market_listings
                    WHERE id = $1 AND status = 'active' AND expires_at > NOW()
                    FOR UPDATE
                    """,
                    listing_id,
                )
                if not listing:
                    return None

                if listing["seller_id"] == buyer_id:
                    return None  # 自分の出品は購入不可

                total = listing["price_per_unit"] * listing["quantity"]
                fee = max(1, math.floor(total * fee_rate))
                total_with_fee = total + fee

                # 買い手コイン消費
                spent = await conn.fetchrow(
                    """
                    UPDATE virtual_currency
                    SET balance = balance - $2,
                        total_spent = total_spent + $2,
                        updated_at = $3
                    WHERE user_id = $1 AND balance >= $2
                    RETURNING balance
                    """,
                    buyer_id, total_with_fee, datetime.now(UTC),
                )
                if not spent:
                    return None

                # 売り手コイン加算 (手数料控除前の金額)
                await conn.execute(
                    """
                    UPDATE virtual_currency
                    SET balance = balance + $2,
                        total_earned = total_earned + $2,
                        updated_at = $3
                    WHERE user_id = $1
                    """,
                    listing["seller_id"], total, datetime.now(UTC),
                )

                # 買い手インベントリに追加
                await conn.execute(
                    """
                    INSERT INTO user_inventory (user_id, item_id, quantity, acquired_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, item_id)
                    DO UPDATE SET quantity = user_inventory.quantity + $3
                    """,
                    buyer_id, listing["item_id"],
                    listing["quantity"], datetime.now(UTC),
                )

                # 出品ステータス更新
                await conn.execute(
                    "UPDATE market_listings SET status = 'sold' WHERE id = $1",
                    listing_id,
                )

                # 取引記録
                await conn.execute(
                    """
                    INSERT INTO market_transactions
                        (listing_id, seller_id, buyer_id, item_id,
                         quantity, price_per_unit, total_amount, fee)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    listing_id, listing["seller_id"], buyer_id,
                    listing["item_id"], listing["quantity"],
                    listing["price_per_unit"], total, fee,
                )

        return {
            "listing_id": listing_id,
            "item_id": listing["item_id"],
            "quantity": listing["quantity"],
            "total": total,
            "fee": fee,
            "balance": spent["balance"],
        }

    async def cancel_listing(self, seller_id: int, listing_id: int) -> bool:
        """出品キャンセル (アイテムをインベントリに返却)"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                listing = await conn.fetchrow(
                    "SELECT * FROM market_listings WHERE id = $1 AND seller_id = $2 AND status = 'active' FOR UPDATE",
                    listing_id, seller_id,
                )
                if not listing:
                    return False

                # インベントリに返却
                await conn.execute(
                    """
                    INSERT INTO user_inventory (user_id, item_id, quantity, acquired_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, item_id)
                    DO UPDATE SET quantity = user_inventory.quantity + $3
                    """,
                    seller_id, listing["item_id"],
                    listing["quantity"], datetime.now(UTC),
                )

                await conn.execute(
                    "UPDATE market_listings SET status = 'cancelled' WHERE id = $1",
                    listing_id,
                )
        return True

    async def get_user_listings(
        self, user_id: int, status: str | None = None
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT ml.*, si.name, si.emoji, si.rarity
                    FROM market_listings ml
                    JOIN shop_items si ON si.id = ml.item_id
                    WHERE ml.seller_id = $1 AND ml.status = $2
                    ORDER BY ml.created_at DESC
                    """,
                    user_id, status,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT ml.*, si.name, si.emoji, si.rarity
                    FROM market_listings ml
                    JOIN shop_items si ON si.id = ml.item_id
                    WHERE ml.seller_id = $1
                    ORDER BY ml.created_at DESC
                    """,
                    user_id,
                )
        return [dict(r) for r in rows]

    async def expire_listings(self) -> int:
        """期限切れ出品を一括処理"""
        count = 0
        async with self.db_pool.acquire() as conn:
            expired = await conn.fetch(
                "SELECT * FROM market_listings WHERE status = 'active' AND expires_at <= NOW()"
            )
            for listing in expired:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE market_listings SET status = 'expired' WHERE id = $1",
                        listing["id"],
                    )
                    # アイテムをインベントリに返却
                    await conn.execute(
                        """
                        INSERT INTO user_inventory (user_id, item_id, quantity, acquired_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (user_id, item_id)
                        DO UPDATE SET quantity = user_inventory.quantity + $3
                        """,
                        listing["seller_id"], listing["item_id"],
                        listing["quantity"], datetime.now(UTC),
                    )
                count += 1
        return count

    async def get_item_price_history(
        self, item_id: int, days: int = 30
    ) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM item_price_history
                WHERE item_id = $1
                  AND recorded_date >= CURRENT_DATE - $2::INT
                ORDER BY recorded_date
                """,
                item_id, days,
            )
        return [dict(r) for r in rows]

    async def update_item_price_history(self) -> None:
        """日次: アイテム価格履歴を更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO item_price_history (item_id, avg_price, min_price, max_price, volume, recorded_date)
                SELECT
                    mt.item_id,
                    AVG(mt.price_per_unit)::INT,
                    MIN(mt.price_per_unit),
                    MAX(mt.price_per_unit),
                    SUM(mt.quantity),
                    CURRENT_DATE
                FROM market_transactions mt
                WHERE mt.created_at >= CURRENT_DATE
                  AND mt.created_at < CURRENT_DATE + 1
                GROUP BY mt.item_id
                ON CONFLICT (item_id, recorded_date) DO UPDATE SET
                    avg_price = EXCLUDED.avg_price,
                    min_price = EXCLUDED.min_price,
                    max_price = EXCLUDED.max_price,
                    volume = EXCLUDED.volume
                """
            )
