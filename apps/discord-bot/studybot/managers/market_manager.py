"""投資市場マネージャー — 株式・貯金・フリマのビジネスロジック"""

import asyncio
import logging
import math
from datetime import UTC, datetime, timedelta

from studybot.config.constants import MARKET_CONFIG, SAVINGS_CONFIG, STOCK_CONFIG
from studybot.repositories.market_repository import MarketRepository

logger = logging.getLogger(__name__)


class MarketManager:
    """投資市場の全ビジネスロジック"""

    def __init__(self, db_pool) -> None:
        self.repository = MarketRepository(db_pool)
        self._price_lock = asyncio.Lock()

    # ===== 株式市場 =====

    async def get_all_stocks(self) -> list[dict]:
        stocks = await self.repository.get_all_stocks()
        for s in stocks:
            s["change_pct"] = _calc_change_pct(s["current_price"], s["previous_close"])
        return stocks

    async def get_stock_detail(self, symbol: str) -> dict | None:
        stock = await self.repository.get_stock_by_symbol(symbol)
        if not stock:
            return None
        stock["change_pct"] = _calc_change_pct(stock["current_price"], stock["previous_close"])
        stock["history"] = await self.repository.get_price_history(stock["id"], 30)
        return stock

    async def buy_stock(self, user_id: int, symbol: str, shares: int) -> dict:
        if shares <= 0:
            return {"error": "購入株数は1以上を指定してください"}
        if shares > STOCK_CONFIG["max_shares_per_trade"]:
            return {"error": f"1回の取引は最大{STOCK_CONFIG['max_shares_per_trade']}株です"}

        stock = await self.repository.get_stock_by_symbol(symbol)
        if not stock or not stock["active"]:
            return {"error": f"銘柄 {symbol} が見つかりません"}

        price = stock["current_price"]
        total_cost = price * shares

        result = await self.repository.buy_stock(user_id, stock["id"], shares, price)
        if not result:
            return {"error": f"コインが不足しています（必要: {total_cost:,} 🪙）"}

        return {
            "symbol": symbol,
            "name": stock["name"],
            "emoji": stock["emoji"],
            "shares": shares,
            "price": price,
            "total": total_cost,
            "balance": result["balance"],
        }

    async def sell_stock(self, user_id: int, symbol: str, shares: int) -> dict:
        if shares <= 0:
            return {"error": "売却株数は1以上を指定してください"}
        if shares > STOCK_CONFIG["max_shares_per_trade"]:
            return {"error": f"1回の取引は最大{STOCK_CONFIG['max_shares_per_trade']}株です"}

        stock = await self.repository.get_stock_by_symbol(symbol)
        if not stock:
            return {"error": f"銘柄 {symbol} が見つかりません"}

        price = stock["current_price"]
        result = await self.repository.sell_stock(user_id, stock["id"], shares, price)
        if not result:
            return {"error": f"{symbol} を {shares} 株保有していません"}

        return {
            "symbol": symbol,
            "name": stock["name"],
            "emoji": stock["emoji"],
            "shares": shares,
            "price": price,
            "total": result["total"],
            "profit": result["profit"],
            "balance": result["balance"],
        }

    async def get_portfolio(self, user_id: int) -> dict:
        holdings = await self.repository.get_user_holdings(user_id)
        total_value = 0
        total_invested = 0
        for h in holdings:
            market_value = h["shares"] * h["current_price"]
            h["market_value"] = market_value
            h["profit"] = market_value - h["total_invested"]
            h["profit_pct"] = (
                round((h["profit"] / h["total_invested"]) * 100, 1)
                if h["total_invested"] > 0
                else 0.0
            )
            total_value += market_value
            total_invested += h["total_invested"]

        return {
            "holdings": holdings,
            "total_value": total_value,
            "total_invested": total_invested,
            "total_profit": total_value - total_invested,
            "total_profit_pct": (
                round(((total_value - total_invested) / total_invested) * 100, 1)
                if total_invested > 0
                else 0.0
            ),
        }

    async def get_stock_history(self, symbol: str, days: int = 30) -> list[dict]:
        stock = await self.repository.get_stock_by_symbol(symbol)
        if not stock:
            return []
        return await self.repository.get_price_history(stock["id"], days)

    async def get_transactions(self, user_id: int, limit: int = 20, offset: int = 0) -> dict:
        items = await self.repository.get_stock_transactions(user_id, limit, offset)
        total = await self.repository.get_stock_transaction_count(user_id)
        return {"items": items, "total": total, "offset": offset, "limit": limit}

    async def update_all_prices(self) -> list[dict]:
        """全銘柄の株価を更新 (毎時タスク)"""
        async with self._price_lock:
            stocks = await self.repository.get_all_stocks()
            results = []
            now = datetime.now(UTC)

            for stock in stocks:
                try:
                    new_price = await self._calculate_new_price(stock, now)
                    await self.repository.update_stock_price(stock["id"], new_price)
                    results.append(
                        {
                            "symbol": stock["symbol"],
                            "old_price": stock["current_price"],
                            "new_price": new_price,
                        }
                    )
                except Exception as e:
                    logger.error(f"株価更新エラー {stock['symbol']}: {e}")

            return results

    async def save_daily_snapshots(self) -> None:
        """日次スナップショット保存"""
        stocks = await self.repository.get_all_stocks()
        now = datetime.now(UTC)
        today = now.date()
        week_start = now - timedelta(days=7)

        for stock in stocks:
            try:
                # 今週の学習量
                minutes = await self.repository.get_study_minutes_for_topic(
                    stock["topic_keyword"], week_start, now
                )
                # 今日の取引量
                volume = await self.repository.get_net_buy_volume(
                    stock["id"], datetime.combine(today, datetime.min.time(), tzinfo=UTC)
                )

                await self.repository.save_price_snapshot(
                    stock_id=stock["id"],
                    price=stock["current_price"],
                    volume=abs(volume),
                    study_minutes=minutes,
                    study_sessions=0,
                    recorded_date=today,
                )

                # 前日終値を更新
                await self.repository.update_stock_price(
                    stock["id"],
                    stock["current_price"],
                    previous_close=stock["current_price"],
                )
            except Exception as e:
                logger.error(f"スナップショット保存エラー {stock['symbol']}: {e}")

    async def _calculate_new_price(self, stock: dict, now: datetime) -> int:
        """株価アルゴリズム: EMA + トレンド + 売買圧力"""
        # 1. activity_trend = (今週 + 1) / (先週 + 1)
        this_week_start = now - timedelta(days=7)
        last_week_start = now - timedelta(days=14)
        last_week_end = now - timedelta(days=7)

        this_week = await self.repository.get_study_minutes_for_topic(
            stock["topic_keyword"], this_week_start, now
        )
        last_week = await self.repository.get_study_minutes_for_topic(
            stock["topic_keyword"], last_week_start, last_week_end
        )

        activity_trend = (this_week + 1) / (last_week + 1)

        # 2. activity_price = base_price × activity_trend
        activity_price = stock["base_price"] * activity_trend

        # 3. EMA: new_price = ema_weight × activity_price + (1 - ema_weight) × current_price
        ema_weight = STOCK_CONFIG["ema_weight"]
        ema_price = ema_weight * activity_price + (1 - ema_weight) * stock["current_price"]

        # 4. 売買圧力
        net_volume = await self.repository.get_net_buy_volume(
            stock["id"], now - timedelta(hours=STOCK_CONFIG["price_update_hours"])
        )
        pressure = net_volume * STOCK_CONFIG["buy_pressure_factor"]
        raw_price = ema_price + pressure

        # 5. サーキットブレーカー: 前日終値 ±15% 以内
        prev_close = stock["previous_close"] or stock["base_price"]
        cb_pct = STOCK_CONFIG["circuit_breaker_pct"]
        lower_bound = math.floor(prev_close * (1 - cb_pct))
        upper_bound = math.ceil(prev_close * (1 + cb_pct))
        clamped = max(lower_bound, min(upper_bound, raw_price))

        # 6. 絶対上下限
        final = max(STOCK_CONFIG["min_price"], min(STOCK_CONFIG["max_price"], int(clamped)))
        return final

    # ===== 貯金銀行 =====

    async def get_savings_status(self, user_id: int) -> dict:
        accounts = await self.repository.get_savings_accounts(user_id)
        total_savings = sum(a["balance"] for a in accounts)
        total_interest = sum(a["total_interest_earned"] for a in accounts)
        return {
            "accounts": accounts,
            "total_savings": total_savings,
            "total_interest": total_interest,
        }

    async def deposit(self, user_id: int, amount: int, account_type: str = "regular") -> dict:
        if amount < SAVINGS_CONFIG["min_deposit"]:
            return {"error": f"最低預金額は {SAVINGS_CONFIG['min_deposit']} 🪙 です"}

        if account_type not in ("regular", "fixed"):
            return {"error": "口座タイプは regular か fixed を指定してください"}

        if account_type == "regular":
            rate = SAVINGS_CONFIG["regular_daily_rate"]
            lock_days = 0
        else:
            rate = SAVINGS_CONFIG["fixed_daily_rate"]
            lock_days = SAVINGS_CONFIG["fixed_lock_days"]

        result = await self.repository.deposit(user_id, account_type, amount, rate, lock_days)
        if not result:
            return {"error": "コインが不足しています"}

        type_label = "普通預金" if account_type == "regular" else "定期預金"
        return {
            "account_type": account_type,
            "type_label": type_label,
            "amount": amount,
            "balance": result["balance"],
            "interest_rate": rate,
            "lock_days": lock_days,
            "maturity_date": result.get("maturity_date"),
        }

    async def withdraw(self, user_id: int, amount: int, account_type: str = "regular") -> dict:
        if amount <= 0:
            return {"error": "引き出し額は1以上を指定してください"}

        if account_type not in ("regular", "fixed"):
            return {"error": "口座タイプは regular か fixed を指定してください"}

        # 定期預金の満期チェック
        if account_type == "fixed":
            account = await self.repository.get_savings_account(user_id, "fixed")
            if account and account["maturity_date"]:
                if datetime.now(UTC) < account["maturity_date"]:
                    remaining = (account["maturity_date"] - datetime.now(UTC)).days
                    return {
                        "error": (
                            f"定期預金の満期まであと {remaining} 日です。"
                            "満期前の引き出しはできません。"
                        )
                    }

        result = await self.repository.withdraw(user_id, account_type, amount)
        if not result:
            return {"error": "残高不足または口座が見つかりません"}

        type_label = "普通預金" if account_type == "regular" else "定期預金"
        return {
            "account_type": account_type,
            "type_label": type_label,
            "amount": amount,
            "new_balance": result["new_balance"],
        }

    async def process_daily_interest(self) -> list[dict]:
        return await self.repository.calculate_and_apply_interest()

    async def get_interest_history(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self.repository.get_interest_history(user_id, limit)

    # ===== フリーマーケット =====

    async def create_listing(self, user_id: int, item_id: int, quantity: int, price: int) -> dict:
        if quantity <= 0:
            return {"error": "出品数量は1以上を指定してください"}
        if price < MARKET_CONFIG["min_price"] or price > MARKET_CONFIG["max_price"]:
            return {
                "error": (
                    f"価格は {MARKET_CONFIG['min_price']}〜"
                    f"{MARKET_CONFIG['max_price']:,} 🪙 の範囲で"
                    "指定してください"
                )
            }

        # 出品数上限チェック
        user_listings = await self.repository.get_user_listings(user_id, status="active")
        if len(user_listings) >= MARKET_CONFIG["max_listings_per_user"]:
            return {
                "error": f"出品数上限 ({MARKET_CONFIG['max_listings_per_user']}件) に達しています"
            }

        expires_at = datetime.now(UTC) + timedelta(days=MARKET_CONFIG["listing_duration_days"])
        result = await self.repository.create_listing(user_id, item_id, quantity, price, expires_at)
        if not result:
            return {"error": "アイテムが不足しているか、出品に失敗しました"}

        return {
            "listing_id": result["id"],
            "item_id": item_id,
            "quantity": quantity,
            "price": price,
            "expires_at": expires_at,
        }

    async def get_listings(
        self, item_id: int | None = None, limit: int = 20, offset: int = 0
    ) -> dict:
        items = await self.repository.get_active_listings(item_id, limit, offset)
        total = await self.repository.get_active_listing_count(item_id)
        return {"items": items, "total": total, "offset": offset, "limit": limit}

    async def buy_listing(self, buyer_id: int, listing_id: int) -> dict:
        listing = await self.repository.get_listing(listing_id)
        if not listing:
            return {"error": "出品が見つかりません"}
        if listing["status"] != "active":
            return {"error": "この出品は既に終了しています"}
        if listing["seller_id"] == buyer_id:
            return {"error": "自分の出品は購入できません"}

        total = listing["price_per_unit"] * listing["quantity"]
        fee = max(1, math.floor(total * MARKET_CONFIG["fee_rate"]))

        result = await self.repository.buy_listing(buyer_id, listing_id, MARKET_CONFIG["fee_rate"])
        if not result:
            return {
                "error": (
                    f"コインが不足しています"
                    f"（必要: {total + fee:,} 🪙 = "
                    f"価格 {total:,} + 手数料 {fee:,}）"
                )
            }

        return {
            "listing_id": listing_id,
            "item_name": listing.get("name", ""),
            "item_emoji": listing.get("emoji", ""),
            "quantity": listing["quantity"],
            "total": result["total"],
            "fee": result["fee"],
            "balance": result["balance"],
        }

    async def cancel_listing(self, user_id: int, listing_id: int) -> dict:
        success = await self.repository.cancel_listing(user_id, listing_id)
        if not success:
            return {"error": "出品が見つからないか、キャンセルできません"}
        return {"listing_id": listing_id, "cancelled": True}

    async def get_my_listings(self, user_id: int) -> list[dict]:
        return await self.repository.get_user_listings(user_id)

    async def get_item_price_history(self, item_id: int, days: int = 30) -> list[dict]:
        return await self.repository.get_item_price_history(item_id, days)

    async def process_expired_listings(self) -> int:
        return await self.repository.expire_listings()

    async def process_daily_item_prices(self) -> None:
        await self.repository.update_item_price_history()


def _calc_change_pct(current: int, previous: int) -> float:
    if previous == 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 1)
