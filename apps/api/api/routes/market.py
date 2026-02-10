"""投資市場 API エンドポイント — 株式・貯金・フリマ"""

import logging
import math
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import (
    BuyListingResponse,
    CreateListingRequest,
    InterestHistoryResponse,
    ItemPriceHistoryResponse,
    MarketListingResponse,
    PaginatedResponse,
    PortfolioResponse,
    SavingsAccountResponse,
    SavingsDepositRequest,
    SavingsStatusResponse,
    SavingsTransactionResponse,
    SavingsWithdrawRequest,
    StockDetailResponse,
    StockHolding,
    StockPriceHistory,
    StockResponse,
    StockTradeRequest,
    StockTradeResponse,
    StockTransactionResponse,
    UserListingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])

# ===== 株式市場 =====


@router.get("/stocks", response_model=list[StockResponse])
async def get_stocks(current_user: dict = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM study_stocks WHERE active = true ORDER BY symbol")
    result = []
    for r in rows:
        change_pct = 0.0
        if r["previous_close"] > 0:
            change_pct = round(
                ((r["current_price"] - r["previous_close"]) / r["previous_close"]) * 100, 1
            )
        result.append(
            StockResponse(
                id=r["id"],
                symbol=r["symbol"],
                name=r["name"],
                topic_keyword=r["topic_keyword"],
                description=r["description"] or "",
                emoji=r["emoji"],
                sector=r["sector"] or "",
                base_price=r["base_price"],
                current_price=r["current_price"],
                previous_close=r["previous_close"],
                total_shares=r["total_shares"],
                circulating_shares=r["circulating_shares"],
                change_pct=change_pct,
            )
        )
    return result


@router.get("/stocks/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(symbol: str, current_user: dict = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        stock = await conn.fetchrow("SELECT * FROM study_stocks WHERE symbol = $1", symbol.upper())
        if not stock:
            raise HTTPException(status_code=404, detail="銘柄が見つかりません")

        history_rows = await conn.fetch(
            """
            SELECT price, volume, study_minutes, study_sessions, recorded_date
            FROM stock_price_history
            WHERE stock_id = $1
            ORDER BY recorded_date DESC LIMIT 30
            """,
            stock["id"],
        )

    change_pct = 0.0
    if stock["previous_close"] > 0:
        change_pct = round(
            ((stock["current_price"] - stock["previous_close"]) / stock["previous_close"]) * 100, 1
        )

    history = [
        StockPriceHistory(
            price=h["price"],
            volume=h["volume"],
            study_minutes=h["study_minutes"],
            study_sessions=h["study_sessions"],
            recorded_date=h["recorded_date"],
        )
        for h in reversed(history_rows)
    ]

    return StockDetailResponse(
        id=stock["id"],
        symbol=stock["symbol"],
        name=stock["name"],
        topic_keyword=stock["topic_keyword"],
        description=stock["description"] or "",
        emoji=stock["emoji"],
        sector=stock["sector"] or "",
        base_price=stock["base_price"],
        current_price=stock["current_price"],
        previous_close=stock["previous_close"],
        total_shares=stock["total_shares"],
        circulating_shares=stock["circulating_shares"],
        change_pct=change_pct,
        history=history,
    )


@router.get("/stocks/{symbol}/history", response_model=list[StockPriceHistory])
async def get_stock_history(
    symbol: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
):
    pool = get_pool()
    async with pool.acquire() as conn:
        stock = await conn.fetchrow("SELECT id FROM study_stocks WHERE symbol = $1", symbol.upper())
        if not stock:
            raise HTTPException(status_code=404, detail="銘柄が見つかりません")

        rows = await conn.fetch(
            """
            SELECT price, volume, study_minutes, study_sessions, recorded_date
            FROM stock_price_history
            WHERE stock_id = $1 AND recorded_date >= CURRENT_DATE - $2::INT
            ORDER BY recorded_date
            """,
            stock["id"],
            days,
        )

    return [
        StockPriceHistory(
            price=r["price"],
            volume=r["volume"],
            study_minutes=r["study_minutes"],
            study_sessions=r["study_sessions"],
            recorded_date=r["recorded_date"],
        )
        for r in rows
    ]


@router.post("/stocks/{symbol}/buy", response_model=StockTradeResponse)
async def buy_stock(
    symbol: str,
    req: StockTradeRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        stock = await conn.fetchrow(
            "SELECT * FROM study_stocks WHERE symbol = $1 AND active = true",
            symbol.upper(),
        )
        if not stock:
            raise HTTPException(status_code=404, detail="銘柄が見つかりません")

        price = stock["current_price"]
        total_cost = price * req.shares

        async with conn.transaction():
            spent = await conn.fetchrow(
                """
                UPDATE virtual_currency
                SET balance = balance - $2, total_spent = total_spent + $2, updated_at = $3
                WHERE user_id = $1 AND balance >= $2
                RETURNING balance
                """,
                user_id,
                total_cost,
                datetime.now(UTC),
            )
            if not spent:
                raise HTTPException(status_code=400, detail=f"コイン不足 (必要: {total_cost:,})")

            # 保有株更新
            existing = await conn.fetchrow(
                "SELECT shares, total_invested FROM user_stock_holdings WHERE user_id = $1 AND stock_id = $2",
                user_id,
                stock["id"],
            )
            if existing:
                new_shares = existing["shares"] + req.shares
                new_invested = existing["total_invested"] + total_cost
                new_avg = math.floor(new_invested / new_shares)
                await conn.execute(
                    """
                    UPDATE user_stock_holdings
                    SET shares = $3, avg_buy_price = $4, total_invested = $5, updated_at = $6
                    WHERE user_id = $1 AND stock_id = $2
                    """,
                    user_id,
                    stock["id"],
                    new_shares,
                    new_avg,
                    new_invested,
                    datetime.now(UTC),
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO user_stock_holdings (user_id, stock_id, shares, avg_buy_price, total_invested, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    user_id,
                    stock["id"],
                    req.shares,
                    price,
                    total_cost,
                    datetime.now(UTC),
                )

            await conn.execute(
                "UPDATE study_stocks SET circulating_shares = circulating_shares + $2 WHERE id = $1",
                stock["id"],
                req.shares,
            )
            await conn.execute(
                """
                INSERT INTO stock_transactions (user_id, stock_id, transaction_type, shares, price_per_share, total_amount)
                VALUES ($1, $2, 'buy', $3, $4, $5)
                """,
                user_id,
                stock["id"],
                req.shares,
                price,
                total_cost,
            )

    return StockTradeResponse(
        symbol=stock["symbol"],
        name=stock["name"],
        emoji=stock["emoji"],
        shares=req.shares,
        price=price,
        total=total_cost,
        balance=spent["balance"],
    )


@router.post("/stocks/{symbol}/sell", response_model=StockTradeResponse)
async def sell_stock(
    symbol: str,
    req: StockTradeRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        stock = await conn.fetchrow(
            "SELECT * FROM study_stocks WHERE symbol = $1",
            symbol.upper(),
        )
        if not stock:
            raise HTTPException(status_code=404, detail="銘柄が見つかりません")

        price = stock["current_price"]
        total_amount = price * req.shares

        async with conn.transaction():
            holding = await conn.fetchrow(
                "SELECT * FROM user_stock_holdings WHERE user_id = $1 AND stock_id = $2 AND shares >= $3",
                user_id,
                stock["id"],
                req.shares,
            )
            if not holding:
                raise HTTPException(status_code=400, detail="保有株数が不足しています")

            profit = total_amount - (holding["avg_buy_price"] * req.shares)
            new_shares = holding["shares"] - req.shares

            if new_shares == 0:
                await conn.execute(
                    "DELETE FROM user_stock_holdings WHERE user_id = $1 AND stock_id = $2",
                    user_id,
                    stock["id"],
                )
            else:
                ratio = new_shares / holding["shares"]
                new_invested = math.floor(holding["total_invested"] * ratio)
                new_avg = math.floor(new_invested / new_shares)
                await conn.execute(
                    """
                    UPDATE user_stock_holdings
                    SET shares = $3, avg_buy_price = $4, total_invested = $5, updated_at = $6
                    WHERE user_id = $1 AND stock_id = $2
                    """,
                    user_id,
                    stock["id"],
                    new_shares,
                    new_avg,
                    new_invested,
                    datetime.now(UTC),
                )

            await conn.execute(
                "UPDATE study_stocks SET circulating_shares = GREATEST(circulating_shares - $2, 0) WHERE id = $1",
                stock["id"],
                req.shares,
            )

            balance_row = await conn.fetchrow(
                """
                UPDATE virtual_currency
                SET balance = balance + $2, total_earned = total_earned + $2, updated_at = $3
                WHERE user_id = $1
                RETURNING balance
                """,
                user_id,
                total_amount,
                datetime.now(UTC),
            )

            await conn.execute(
                """
                INSERT INTO stock_transactions (user_id, stock_id, transaction_type, shares, price_per_share, total_amount)
                VALUES ($1, $2, 'sell', $3, $4, $5)
                """,
                user_id,
                stock["id"],
                req.shares,
                price,
                total_amount,
            )

    return StockTradeResponse(
        symbol=stock["symbol"],
        name=stock["name"],
        emoji=stock["emoji"],
        shares=req.shares,
        price=price,
        total=total_amount,
        balance=balance_row["balance"] if balance_row else 0,
        profit=profit,
    )


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
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

    holdings = []
    total_value = 0
    total_invested = 0
    for r in rows:
        mv = r["shares"] * r["current_price"]
        profit = mv - r["total_invested"]
        pct = round((profit / r["total_invested"]) * 100, 1) if r["total_invested"] > 0 else 0.0
        holdings.append(
            StockHolding(
                symbol=r["symbol"],
                name=r["name"],
                emoji=r["emoji"],
                sector=r["sector"] or "",
                shares=r["shares"],
                avg_buy_price=r["avg_buy_price"],
                total_invested=r["total_invested"],
                current_price=r["current_price"],
                market_value=mv,
                profit=profit,
                profit_pct=pct,
            )
        )
        total_value += mv
        total_invested += r["total_invested"]

    tp = total_value - total_invested
    tpct = round((tp / total_invested) * 100, 1) if total_invested > 0 else 0.0

    return PortfolioResponse(
        holdings=holdings,
        total_value=total_value,
        total_invested=total_invested,
        total_profit=tp,
        total_profit_pct=tpct,
    )


@router.get("/portfolio/summary")
async def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    portfolio = await get_portfolio(current_user)
    return {
        "total_value": portfolio.total_value,
        "total_invested": portfolio.total_invested,
        "total_profit": portfolio.total_profit,
        "total_profit_pct": portfolio.total_profit_pct,
        "stock_count": len(portfolio.holdings),
    }


@router.get("/transactions", response_model=PaginatedResponse[StockTransactionResponse])
async def get_transactions(
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM stock_transactions WHERE user_id = $1", user_id
        )
        rows = await conn.fetch(
            """
            SELECT t.*, s.symbol, s.name, s.emoji
            FROM stock_transactions t
            JOIN study_stocks s ON s.id = t.stock_id
            WHERE t.user_id = $1
            ORDER BY t.created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )

    items = [
        StockTransactionResponse(
            id=r["id"],
            symbol=r["symbol"],
            name=r["name"],
            emoji=r["emoji"],
            transaction_type=r["transaction_type"],
            shares=r["shares"],
            price_per_share=r["price_per_share"],
            total_amount=r["total_amount"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


# ===== 貯金銀行 =====


@router.get("/savings", response_model=SavingsStatusResponse)
async def get_savings(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM savings_accounts WHERE user_id = $1 ORDER BY account_type",
            user_id,
        )

    accounts = [
        SavingsAccountResponse(
            id=r["id"],
            account_type=r["account_type"],
            balance=r["balance"],
            interest_rate=r["interest_rate"],
            lock_days=r["lock_days"],
            maturity_date=r["maturity_date"],
            total_interest_earned=r["total_interest_earned"],
            last_interest_at=r["last_interest_at"],
        )
        for r in rows
    ]
    total_savings = sum(a.balance for a in accounts)
    total_interest = sum(a.total_interest_earned for a in accounts)

    return SavingsStatusResponse(
        accounts=accounts,
        total_savings=total_savings,
        total_interest=total_interest,
    )


@router.post("/savings/deposit", response_model=SavingsTransactionResponse)
async def deposit(
    req: SavingsDepositRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    now = datetime.now(UTC)

    if req.account_type == "regular":
        rate = 0.001
        lock_days = 0
    else:
        rate = 0.003
        lock_days = 7

    maturity_date = now + timedelta(days=lock_days) if lock_days > 0 else None

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            spent = await conn.fetchrow(
                """
                UPDATE virtual_currency
                SET balance = balance - $2, total_spent = total_spent + $2, updated_at = $3
                WHERE user_id = $1 AND balance >= $2
                RETURNING balance
                """,
                user_id,
                req.amount,
                now,
            )
            if not spent:
                raise HTTPException(status_code=400, detail="コイン不足")

            row = await conn.fetchrow(
                """
                INSERT INTO savings_accounts
                    (user_id, account_type, balance, interest_rate, lock_days, maturity_date, last_interest_at, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
                ON CONFLICT (user_id, account_type) DO UPDATE SET
                    balance = savings_accounts.balance + $3,
                    maturity_date = CASE WHEN $6 IS NOT NULL THEN $6 ELSE savings_accounts.maturity_date END,
                    last_interest_at = COALESCE(savings_accounts.last_interest_at, $7)
                RETURNING *
                """,
                user_id,
                req.account_type,
                req.amount,
                rate,
                lock_days,
                maturity_date,
                now,
            )

    type_label = "普通預金" if req.account_type == "regular" else "定期預金"
    return SavingsTransactionResponse(
        account_type=req.account_type,
        type_label=type_label,
        amount=req.amount,
        balance=row["balance"],
        interest_rate=rate,
        lock_days=lock_days,
    )


@router.post("/savings/withdraw", response_model=SavingsTransactionResponse)
async def withdraw(
    req: SavingsWithdrawRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    now = datetime.now(UTC)

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            account = await conn.fetchrow(
                "SELECT * FROM savings_accounts WHERE user_id = $1 AND account_type = $2 AND balance >= $3",
                user_id,
                req.account_type,
                req.amount,
            )
            if not account:
                raise HTTPException(status_code=400, detail="残高不足または口座なし")

            if req.account_type == "fixed" and account["maturity_date"]:
                if now < account["maturity_date"]:
                    raise HTTPException(status_code=400, detail="定期預金の満期前です")

            new_balance = account["balance"] - req.amount
            await conn.execute(
                "UPDATE savings_accounts SET balance = $3 WHERE user_id = $1 AND account_type = $2",
                user_id,
                req.account_type,
                new_balance,
            )
            await conn.execute(
                """
                UPDATE virtual_currency
                SET balance = balance + $2, total_earned = total_earned + $2, updated_at = $3
                WHERE user_id = $1
                """,
                user_id,
                req.amount,
                now,
            )

    type_label = "普通預金" if req.account_type == "regular" else "定期預金"
    return SavingsTransactionResponse(
        account_type=req.account_type,
        type_label=type_label,
        amount=req.amount,
        new_balance=new_balance,
    )


@router.get("/savings/interest-history", response_model=list[InterestHistoryResponse])
async def get_interest_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ih.*, sa.account_type
            FROM interest_history ih
            JOIN savings_accounts sa ON sa.id = ih.account_id
            WHERE sa.user_id = $1
            ORDER BY ih.calculated_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )

    return [
        InterestHistoryResponse(
            id=r["id"],
            account_type=r["account_type"],
            amount=r["amount"],
            balance_after=r["balance_after"],
            calculated_at=r["calculated_at"],
        )
        for r in rows
    ]


# ===== フリーマーケット =====


@router.get("/flea/listings", response_model=PaginatedResponse[MarketListingResponse])
async def get_listings(
    item_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    pool = get_pool()
    async with pool.acquire() as conn:
        if item_id:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM market_listings WHERE status = 'active' AND expires_at > NOW() AND item_id = $1",
                item_id,
            )
            rows = await conn.fetch(
                """
                SELECT ml.*, si.name, si.emoji, si.rarity, u.username AS seller_name
                FROM market_listings ml
                JOIN shop_items si ON si.id = ml.item_id
                JOIN users u ON u.user_id = ml.seller_id
                WHERE ml.status = 'active' AND ml.expires_at > NOW() AND ml.item_id = $1
                ORDER BY ml.price_per_unit ASC
                LIMIT $2 OFFSET $3
                """,
                item_id,
                limit,
                offset,
            )
        else:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM market_listings WHERE status = 'active' AND expires_at > NOW()"
            )
            rows = await conn.fetch(
                """
                SELECT ml.*, si.name, si.emoji, si.rarity, u.username AS seller_name
                FROM market_listings ml
                JOIN shop_items si ON si.id = ml.item_id
                JOIN users u ON u.user_id = ml.seller_id
                WHERE ml.status = 'active' AND ml.expires_at > NOW()
                ORDER BY ml.created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )

    items = [
        MarketListingResponse(
            id=r["id"],
            seller_id=r["seller_id"],
            seller_name=r["seller_name"],
            item_id=r["item_id"],
            name=r["name"],
            emoji=r["emoji"],
            rarity=r["rarity"],
            quantity=r["quantity"],
            price_per_unit=r["price_per_unit"],
            status=r["status"],
            expires_at=r["expires_at"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("/flea/listings", response_model=UserListingResponse)
async def create_listing(
    req: CreateListingRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=7)

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            inv = await conn.fetchrow(
                "SELECT quantity FROM user_inventory WHERE user_id = $1 AND item_id = $2 AND quantity >= $3",
                user_id,
                req.item_id,
                req.quantity,
            )
            if not inv:
                raise HTTPException(status_code=400, detail="アイテム不足")

            new_qty = inv["quantity"] - req.quantity
            if new_qty == 0:
                await conn.execute(
                    "DELETE FROM user_inventory WHERE user_id = $1 AND item_id = $2",
                    user_id,
                    req.item_id,
                )
            else:
                await conn.execute(
                    "UPDATE user_inventory SET quantity = $3 WHERE user_id = $1 AND item_id = $2",
                    user_id,
                    req.item_id,
                    new_qty,
                )

            row = await conn.fetchrow(
                """
                INSERT INTO market_listings (seller_id, item_id, quantity, price_per_unit, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                user_id,
                req.item_id,
                req.quantity,
                req.price_per_unit,
                expires_at,
            )

        item = await conn.fetchrow(
            "SELECT name, emoji, rarity FROM shop_items WHERE id = $1", req.item_id
        )

    return UserListingResponse(
        id=row["id"],
        item_id=row["item_id"],
        name=item["name"],
        emoji=item["emoji"],
        rarity=item["rarity"],
        quantity=row["quantity"],
        price_per_unit=row["price_per_unit"],
        status=row["status"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
    )


@router.post("/flea/listings/{listing_id}/buy", response_model=BuyListingResponse)
async def buy_listing(
    listing_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    fee_rate = 0.05
    now = datetime.now(UTC)

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            listing = await conn.fetchrow(
                "SELECT * FROM market_listings WHERE id = $1 AND status = 'active' AND expires_at > NOW() FOR UPDATE",
                listing_id,
            )
            if not listing:
                raise HTTPException(status_code=404, detail="出品が見つかりません")
            if listing["seller_id"] == user_id:
                raise HTTPException(status_code=400, detail="自分の出品は購入できません")

            total = listing["price_per_unit"] * listing["quantity"]
            fee = max(1, math.floor(total * fee_rate))
            total_with_fee = total + fee

            spent = await conn.fetchrow(
                """
                UPDATE virtual_currency
                SET balance = balance - $2, total_spent = total_spent + $2, updated_at = $3
                WHERE user_id = $1 AND balance >= $2
                RETURNING balance
                """,
                user_id,
                total_with_fee,
                now,
            )
            if not spent:
                raise HTTPException(
                    status_code=400, detail=f"コイン不足 (必要: {total_with_fee:,})"
                )

            await conn.execute(
                """
                UPDATE virtual_currency
                SET balance = balance + $2, total_earned = total_earned + $2, updated_at = $3
                WHERE user_id = $1
                """,
                listing["seller_id"],
                total,
                now,
            )

            await conn.execute(
                """
                INSERT INTO user_inventory (user_id, item_id, quantity, acquired_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, item_id) DO UPDATE SET quantity = user_inventory.quantity + $3
                """,
                user_id,
                listing["item_id"],
                listing["quantity"],
                now,
            )

            await conn.execute(
                "UPDATE market_listings SET status = 'sold' WHERE id = $1", listing_id
            )

            await conn.execute(
                """
                INSERT INTO market_transactions
                    (listing_id, seller_id, buyer_id, item_id, quantity, price_per_unit, total_amount, fee)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                listing_id,
                listing["seller_id"],
                user_id,
                listing["item_id"],
                listing["quantity"],
                listing["price_per_unit"],
                total,
                fee,
            )

        item = await conn.fetchrow(
            "SELECT name, emoji FROM shop_items WHERE id = $1", listing["item_id"]
        )

    return BuyListingResponse(
        listing_id=listing_id,
        item_name=item["name"] if item else "",
        item_emoji=item["emoji"] if item else "",
        quantity=listing["quantity"],
        total=total,
        fee=fee,
        balance=spent["balance"],
    )


@router.delete("/flea/listings/{listing_id}")
async def cancel_listing(
    listing_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    now = datetime.now(UTC)

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            listing = await conn.fetchrow(
                "SELECT * FROM market_listings WHERE id = $1 AND seller_id = $2 AND status = 'active' FOR UPDATE",
                listing_id,
                user_id,
            )
            if not listing:
                raise HTTPException(status_code=404, detail="出品が見つかりません")

            await conn.execute(
                """
                INSERT INTO user_inventory (user_id, item_id, quantity, acquired_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, item_id) DO UPDATE SET quantity = user_inventory.quantity + $3
                """,
                user_id,
                listing["item_id"],
                listing["quantity"],
                now,
            )

            await conn.execute(
                "UPDATE market_listings SET status = 'cancelled' WHERE id = $1",
                listing_id,
            )

    return {"status": "cancelled", "listing_id": listing_id}


@router.get("/flea/my-listings", response_model=list[UserListingResponse])
async def get_my_listings(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    pool = get_pool()
    async with pool.acquire() as conn:
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

    return [
        UserListingResponse(
            id=r["id"],
            item_id=r["item_id"],
            name=r["name"],
            emoji=r["emoji"],
            rarity=r["rarity"],
            quantity=r["quantity"],
            price_per_unit=r["price_per_unit"],
            status=r["status"],
            expires_at=r["expires_at"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/flea/items/{item_id}/price-history", response_model=list[ItemPriceHistoryResponse])
async def get_item_price_history(
    item_id: int,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM item_price_history
            WHERE item_id = $1 AND recorded_date >= CURRENT_DATE - $2::INT
            ORDER BY recorded_date
            """,
            item_id,
            days,
        )

    return [
        ItemPriceHistoryResponse(
            avg_price=r["avg_price"],
            min_price=r["min_price"],
            max_price=r["max_price"],
            volume=r["volume"],
            recorded_date=r["recorded_date"],
        )
        for r in rows
    ]
