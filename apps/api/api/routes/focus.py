"""フォーカス/ロック管理ルート"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import (
    FocusHistoryEntry,
    FocusSessionResponse,
    FocusStartRequest,
    LockSettingsResponse,
    LockSettingsUpdateRequest,
    PenaltyUnlockResult,
    UnlockCodeRequest,
    UnlockResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/focus", tags=["focus"])

PENALTY_UNLOCK_RATE = 0.20


@router.get("/status", response_model=FocusSessionResponse | None)
async def get_focus_status(
    current_user: dict = Depends(get_current_user),
):
    """アクティブなフォーカスセッションのステータスを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM phone_lock_sessions
            WHERE user_id = $1 AND state = 'active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            user_id,
        )

    if not row:
        return None

    end_time = row["started_at"] + timedelta(minutes=row["duration_minutes"])
    now = datetime.now(UTC)
    remaining = max(0, int((end_time - now).total_seconds()))

    return FocusSessionResponse(
        session_id=row["id"],
        lock_type=row["lock_type"],
        duration_minutes=row["duration_minutes"],
        coins_bet=row["coins_bet"],
        unlock_level=row.get("unlock_level", 1),
        state=row["state"],
        remaining_seconds=remaining,
        remaining_minutes=remaining // 60,
        end_time=end_time,
        started_at=row["started_at"],
    )


@router.post("/start", response_model=FocusSessionResponse)
async def start_focus(
    request: FocusStartRequest,
    current_user: dict = Depends(get_current_user),
):
    """フォーカスセッションを開始"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        # アクティブセッションチェック
        existing = await conn.fetchrow(
            "SELECT id FROM phone_lock_sessions WHERE user_id = $1 AND state = 'active'",
            user_id,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="既にアクティブなセッションがあります。",
            )

        # コインベットバリデーション
        if request.coins_bet > 0 and (request.coins_bet < 10 or request.coins_bet > 100):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="コインベットは10〜100の範囲で指定してください。",
            )

        row = await conn.fetchrow(
            """
            INSERT INTO phone_lock_sessions
                (user_id, lock_type, duration_minutes, coins_bet,
                 unlock_level, state, started_at)
            VALUES ($1, 'lock', $2, $3, $4, 'active', NOW())
            RETURNING *
            """,
            user_id,
            request.duration,
            request.coins_bet,
            request.unlock_level,
        )

    end_time = row["started_at"] + timedelta(minutes=row["duration_minutes"])
    remaining = max(0, int((end_time - datetime.now(UTC)).total_seconds()))

    return FocusSessionResponse(
        session_id=row["id"],
        lock_type=row["lock_type"],
        duration_minutes=row["duration_minutes"],
        coins_bet=row["coins_bet"],
        unlock_level=row.get("unlock_level", 1),
        state=row["state"],
        remaining_seconds=remaining,
        remaining_minutes=remaining // 60,
        end_time=end_time,
        started_at=row["started_at"],
    )


@router.post("/end", response_model=UnlockResult)
async def end_focus(
    current_user: dict = Depends(get_current_user),
):
    """フォーカスセッションを終了（タイマー完了時）"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM phone_lock_sessions
            WHERE user_id = $1 AND state = 'active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            user_id,
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="アクティブなセッションがありません。",
            )

        # タイマー完了チェック（レベル1のみ自動完了）
        end_time = row["started_at"] + timedelta(minutes=row["duration_minutes"])
        if datetime.now(UTC) < end_time and row.get("unlock_level", 1) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="タイマーがまだ完了していません。",
            )

        await conn.execute(
            """
            UPDATE phone_lock_sessions
            SET state = 'completed', ended_at = NOW()
            WHERE id = $1
            """,
            row["id"],
        )

    return UnlockResult(
        success=True,
        coins_earned=15,
        coins_returned=row["coins_bet"],
        message="フォーカスセッションが完了しました！",
    )


@router.post("/unlock", response_model=UnlockResult)
async def unlock_with_code(
    request: UnlockCodeRequest,
    current_user: dict = Depends(get_current_user),
):
    """コード入力でアンロック"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT * FROM phone_lock_sessions
            WHERE user_id = $1 AND state = 'active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            user_id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="アクティブなセッションがありません。",
            )

        # コード検証
        code_row = await conn.fetchrow(
            """
            SELECT * FROM unlock_codes
            WHERE user_id = $1 AND session_id = $2 AND code = $3
              AND used = FALSE AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
            session["id"],
            request.code,
        )

        if not code_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なコードです。コードが間違っているか、有効期限が切れています。",
            )

        # コードを使用済みに
        await conn.execute(
            "UPDATE unlock_codes SET used = TRUE WHERE id = $1",
            code_row["id"],
        )

        # セッション完了
        await conn.execute(
            """
            UPDATE phone_lock_sessions
            SET state = 'completed', ended_at = NOW()
            WHERE id = $1
            """,
            session["id"],
        )

    return UnlockResult(
        success=True,
        coins_earned=15,
        coins_returned=session["coins_bet"],
        message="コード検証成功！ロックを解除しました。",
    )


@router.post("/penalty-unlock", response_model=PenaltyUnlockResult)
async def penalty_unlock(
    current_user: dict = Depends(get_current_user),
):
    """ペナルティ解除（レベル5: 全ベット+残高20%没収）"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT * FROM phone_lock_sessions
            WHERE user_id = $1 AND state = 'active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            user_id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="アクティブなセッションがありません。",
            )

        if session.get("unlock_level", 1) != 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このセッションはペナルティ解除に対応していません。",
            )

        # 残高取得
        balance_row = await conn.fetchrow(
            "SELECT balance FROM virtual_currency WHERE user_id = $1",
            user_id,
        )
        balance = balance_row["balance"] if balance_row else 0

        penalty_coins = int(balance * PENALTY_UNLOCK_RATE)
        total_lost = session["coins_bet"] + penalty_coins

        # コイン没収
        if total_lost > 0 and balance_row:
            await conn.execute(
                """
                UPDATE virtual_currency
                SET balance = GREATEST(0, balance - $2),
                    total_spent = total_spent + $2,
                    updated_at = NOW()
                WHERE user_id = $1
                """,
                user_id,
                total_lost,
            )

        # セッション中断
        await conn.execute(
            """
            UPDATE phone_lock_sessions
            SET state = 'broken', ended_at = NOW()
            WHERE id = $1
            """,
            session["id"],
        )

    return PenaltyUnlockResult(
        success=True,
        coins_lost=total_lost,
        penalty_rate=PENALTY_UNLOCK_RATE,
        message=f"ペナルティ解除しました。{total_lost}コインを失いました。",
    )


@router.post("/request-code")
async def request_code(
    current_user: dict = Depends(get_current_user),
):
    """コードリクエスト（Bot側で処理）"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT * FROM phone_lock_sessions
            WHERE user_id = $1 AND state = 'active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            user_id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="アクティブなセッションがありません。",
            )

        unlock_level = session.get("unlock_level", 1)
        if unlock_level not in (3, 4):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このアンロックレベルではコードリクエストは不要です。",
            )

        # 既存のpendingリクエストチェック
        existing = await conn.fetchrow(
            """
            SELECT id FROM code_requests
            WHERE user_id = $1 AND session_id = $2 AND status = 'pending'
            """,
            user_id,
            session["id"],
        )

        if existing:
            return {"message": "コードリクエストは既に送信済みです。DMをご確認ください。"}

        await conn.execute(
            """
            INSERT INTO code_requests (user_id, session_id, status)
            VALUES ($1, $2, 'pending')
            """,
            user_id,
            session["id"],
        )

    return {"message": "コードリクエストを送信しました。DiscordのDMをご確認ください。"}


@router.get("/settings", response_model=LockSettingsResponse)
async def get_lock_settings(
    current_user: dict = Depends(get_current_user),
):
    """ロック設定を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM user_lock_settings WHERE user_id = $1",
            user_id,
        )

    if not row:
        return LockSettingsResponse()

    return LockSettingsResponse(
        default_unlock_level=row["default_unlock_level"],
        default_duration=row["default_duration"],
        default_coin_bet=row["default_coin_bet"],
        block_categories=list(row["block_categories"]) if row["block_categories"] else [],
        custom_blocked_urls=(
            list(row["custom_blocked_urls"]) if row["custom_blocked_urls"] else []
        ),
    )


@router.put("/settings", response_model=LockSettingsResponse)
async def update_lock_settings(
    request: LockSettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """ロック設定を更新"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        # 既存設定取得
        existing = await conn.fetchrow(
            "SELECT * FROM user_lock_settings WHERE user_id = $1",
            user_id,
        )

        level = request.default_unlock_level or (
            existing["default_unlock_level"] if existing else 1
        )
        duration = request.default_duration or (existing["default_duration"] if existing else 60)
        bet = (
            request.default_coin_bet
            if request.default_coin_bet is not None
            else (existing["default_coin_bet"] if existing else 0)
        )
        categories = (
            request.block_categories
            if request.block_categories is not None
            else (
                list(existing["block_categories"])
                if existing and existing["block_categories"]
                else []
            )
        )
        urls = (
            request.custom_blocked_urls
            if request.custom_blocked_urls is not None
            else (
                list(existing["custom_blocked_urls"])
                if existing and existing["custom_blocked_urls"]
                else []
            )
        )

        row = await conn.fetchrow(
            """
            INSERT INTO user_lock_settings
                (user_id, default_unlock_level, default_duration,
                 default_coin_bet, block_categories, custom_blocked_urls,
                 updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                default_unlock_level = $2,
                default_duration = $3,
                default_coin_bet = $4,
                block_categories = $5,
                custom_blocked_urls = $6,
                updated_at = NOW()
            RETURNING *
            """,
            user_id,
            level,
            duration,
            bet,
            categories,
            urls,
        )

    return LockSettingsResponse(
        default_unlock_level=row["default_unlock_level"],
        default_duration=row["default_duration"],
        default_coin_bet=row["default_coin_bet"],
        block_categories=list(row["block_categories"]) if row["block_categories"] else [],
        custom_blocked_urls=(
            list(row["custom_blocked_urls"]) if row["custom_blocked_urls"] else []
        ),
    )


@router.get("/history", response_model=list[FocusHistoryEntry])
async def get_focus_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """フォーカスセッション履歴を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM phone_lock_sessions
            WHERE user_id = $1
            ORDER BY started_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )

    return [
        FocusHistoryEntry(
            id=row["id"],
            lock_type=row["lock_type"],
            duration_minutes=row["duration_minutes"],
            coins_bet=row["coins_bet"],
            unlock_level=row.get("unlock_level", 1),
            state=row["state"],
            started_at=row["started_at"],
            ended_at=row.get("ended_at"),
        )
        for row in rows
    ]
