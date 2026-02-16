"""フォーカス/ロック管理ルート"""

import json
import logging
import random
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import (
    ChallengeGenerateRequest,
    ChallengeGenerateResponse,
    ChallengeVerifyRequest,
    ChallengeVerifyResponse,
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

        # ユーザーのロック設定を取得（ブロックカテゴリ/メッセージ用）
        settings_row = await conn.fetchrow(
            "SELECT block_categories, block_message FROM user_lock_settings WHERE user_id = $1",
            user_id,
        ) if row else None

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
        challenge_mode=row.get("challenge_mode", "none") or "none",
        block_categories=(
            list(settings_row["block_categories"])
            if settings_row and settings_row["block_categories"]
            else []
        ),
        block_message=(
            settings_row["block_message"]
            if settings_row and settings_row["block_message"]
            else ""
        ),
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

        # チャレンジモードのバリデーション
        if request.challenge_mode not in ("none", "math", "typing"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="チャレンジモードは none/math/typing のいずれかを指定してください。",
            )

        row = await conn.fetchrow(
            """
            INSERT INTO phone_lock_sessions
                (user_id, lock_type, duration_minutes, coins_bet,
                 unlock_level, challenge_mode, state, started_at)
            VALUES ($1, 'lock', $2, $3, $4, $5, 'active', NOW())
            RETURNING *
            """,
            user_id,
            request.duration,
            request.coins_bet,
            request.unlock_level,
            request.challenge_mode,
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
        challenge_mode=row.get("challenge_mode", "none") or "none",
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
        challenge_mode=row.get("challenge_mode", "none") or "none",
        challenge_difficulty=row.get("challenge_difficulty", 1) or 1,
        block_message=row.get("block_message", "") or "",
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
        ch_mode = (
            request.challenge_mode
            if request.challenge_mode is not None
            else (existing.get("challenge_mode", "none") if existing else "none")
        ) or "none"
        ch_diff = (
            request.challenge_difficulty
            if request.challenge_difficulty is not None
            else (existing.get("challenge_difficulty", 1) if existing else 1)
        ) or 1
        blk_msg = (
            request.block_message
            if request.block_message is not None
            else (existing.get("block_message", "") if existing else "")
        ) or ""

        # カスタムURLバリデーション（最大50件）
        if urls and len(urls) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="カスタムURLは最大50件までです。",
            )

        row = await conn.fetchrow(
            """
            INSERT INTO user_lock_settings
                (user_id, default_unlock_level, default_duration,
                 default_coin_bet, block_categories, custom_blocked_urls,
                 challenge_mode, challenge_difficulty, block_message,
                 updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                default_unlock_level = $2,
                default_duration = $3,
                default_coin_bet = $4,
                block_categories = $5,
                custom_blocked_urls = $6,
                challenge_mode = $7,
                challenge_difficulty = $8,
                block_message = $9,
                updated_at = NOW()
            RETURNING *
            """,
            user_id,
            level,
            duration,
            bet,
            categories,
            urls,
            ch_mode,
            ch_diff,
            blk_msg,
        )

    return LockSettingsResponse(
        default_unlock_level=row["default_unlock_level"],
        default_duration=row["default_duration"],
        default_coin_bet=row["default_coin_bet"],
        block_categories=list(row["block_categories"]) if row["block_categories"] else [],
        custom_blocked_urls=(
            list(row["custom_blocked_urls"]) if row["custom_blocked_urls"] else []
        ),
        challenge_mode=row.get("challenge_mode", "none") or "none",
        challenge_difficulty=row.get("challenge_difficulty", 1) or 1,
        block_message=row.get("block_message", "") or "",
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


# === チャレンジ API ===

# チャレンジ難易度設定（constants.py と同一定義）
_CHALLENGE_DIFFICULTY = {
    1: {"problems": 3, "min_digits": 1, "max_digits": 2, "ops": ["+", "-"]},
    2: {"problems": 4, "min_digits": 1, "max_digits": 2, "ops": ["+", "-", "*"]},
    3: {"problems": 5, "min_digits": 2, "max_digits": 3, "ops": ["+", "-", "*"]},
    4: {"problems": 6, "min_digits": 2, "max_digits": 3, "ops": ["+", "-", "*", "//"]},
    5: {"problems": 8, "min_digits": 2, "max_digits": 4, "ops": ["+", "-", "*", "//"]},
}

_TYPING_PHRASES = [
    "集中して学習に取り組みましょう",
    "今やるべきことに全力を注ごう",
    "スマホを置いて目標に向かって進もう",
    "一歩一歩の積み重ねが大きな成果になる",
    "今この瞬間の努力が未来を変える",
    "諦めずに続ける人だけが目標を達成できる",
    "集中力こそが最強のスキルである",
    "自分との約束を守ることが成長の鍵",
    "目の前の課題に集中すれば結果はついてくる",
    "限られた時間を最大限に活用しよう",
]

CHALLENGE_DISMISS_COOLDOWN = 300  # 5分


@router.post("/challenge/generate", response_model=ChallengeGenerateResponse)
async def generate_challenge(
    request: ChallengeGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """チャレンジを生成（回答はDB保存、クライアントに問題のみ返却）"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        # アクティブセッション必須
        session = await conn.fetchrow(
            """
            SELECT id, challenge_mode FROM phone_lock_sessions
            WHERE user_id = $1 AND state = 'active'
            ORDER BY started_at DESC LIMIT 1
            """,
            user_id,
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="アクティブなセッションがありません。",
            )

        difficulty = request.difficulty
        config = _CHALLENGE_DIFFICULTY.get(difficulty, _CHALLENGE_DIFFICULTY[1])

        if request.challenge_type == "math":
            problems = []
            for _ in range(config["problems"]):
                op = random.choice(config["ops"])
                a = random.randint(
                    10 ** (config["min_digits"] - 1), 10 ** config["max_digits"] - 1
                )
                b = random.randint(
                    10 ** (config["min_digits"] - 1), 10 ** config["max_digits"] - 1
                )
                if op == "//":
                    b = max(b, 2)
                    a = a * b
                expr = f"{a} {op} {b}"
                if op == "+":
                    answer = a + b
                elif op == "-":
                    answer = a - b
                elif op == "*":
                    answer = a * b
                else:
                    answer = a // b
                problems.append({"expression": expr, "answer": answer})

            # DBに保存（answerも含めて）
            row = await conn.fetchrow(
                """
                INSERT INTO challenge_attempts
                    (user_id, session_id, challenge_type, difficulty, problems)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                user_id,
                session["id"],
                "math",
                difficulty,
                json.dumps(problems),
            )

            # クライアントには answer を含めない
            client_problems = [{"expression": p["expression"]} for p in problems]
            return ChallengeGenerateResponse(
                challenge_id=row["id"],
                challenge_type="math",
                difficulty=difficulty,
                problems=client_problems,
            )

        elif request.challenge_type == "typing":
            count = min(difficulty, len(_TYPING_PHRASES))
            phrases = random.sample(_TYPING_PHRASES, count)

            row = await conn.fetchrow(
                """
                INSERT INTO challenge_attempts
                    (user_id, session_id, challenge_type, difficulty, problems)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                user_id,
                session["id"],
                "typing",
                difficulty,
                json.dumps(phrases),
            )

            return ChallengeGenerateResponse(
                challenge_id=row["id"],
                challenge_type="typing",
                difficulty=difficulty,
                problems=phrases,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="challenge_type は math または typing を指定してください。",
            )


@router.post("/challenge/verify", response_model=ChallengeVerifyResponse)
async def verify_challenge(
    request: ChallengeVerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """チャレンジ回答を検証"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        # チャレンジ取得
        attempt = await conn.fetchrow(
            """
            SELECT * FROM challenge_attempts
            WHERE id = $1 AND user_id = $2 AND correct = FALSE
            """,
            request.challenge_id,
            user_id,
        )

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="チャレンジが見つからないか、既に検証済みです。",
            )

        problems = json.loads(attempt["problems"]) if isinstance(attempt["problems"], str) else attempt["problems"]
        answers = request.answers
        ch_type = attempt["challenge_type"]

        if ch_type == "math":
            if len(answers) != len(problems):
                correct = False
                score = 0
            else:
                score = sum(
                    1 for p, a in zip(problems, answers) if p["answer"] == a
                )
                correct = score == len(problems)

            await conn.execute(
                """
                UPDATE challenge_attempts
                SET answers = $2, correct = $3
                WHERE id = $1
                """,
                attempt["id"],
                json.dumps(answers),
                correct,
            )

            dismissed_until = None
            if correct:
                dismissed_until = datetime.now(UTC) + timedelta(
                    seconds=CHALLENGE_DISMISS_COOLDOWN
                )

            return ChallengeVerifyResponse(
                correct=correct,
                score=score,
                total=len(problems),
                dismissed_until=dismissed_until,
            )

        elif ch_type == "typing":
            if len(answers) != len(problems):
                correct = False
                matched = 0
            else:
                matched = sum(1 for o, t in zip(problems, answers) if o == t)
                correct = matched == len(problems)

            accuracy = matched / len(problems) * 100 if problems else 0.0

            await conn.execute(
                """
                UPDATE challenge_attempts
                SET answers = $2, correct = $3
                WHERE id = $1
                """,
                attempt["id"],
                json.dumps(answers),
                correct,
            )

            dismissed_until = None
            if correct:
                dismissed_until = datetime.now(UTC) + timedelta(
                    seconds=CHALLENGE_DISMISS_COOLDOWN
                )

            return ChallengeVerifyResponse(
                correct=correct,
                score=matched,
                total=len(problems),
                accuracy=round(accuracy, 1),
                dismissed_until=dismissed_until,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不明なチャレンジタイプです。",
            )
