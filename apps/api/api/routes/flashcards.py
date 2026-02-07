"""フラッシュカードルート"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from api.database import get_pool
from api.dependencies import get_current_user
from api.models.schemas import DeckStats, Flashcard, FlashcardDeck, ReviewRequest

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


@router.get("/decks", response_model=list[FlashcardDeck])
async def get_my_decks(current_user: dict = Depends(get_current_user)):
    """自分のデッキ一覧を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM flashcard_decks WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )

    return [
        FlashcardDeck(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            card_count=row["card_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/decks/{deck_id}/cards", response_model=list[Flashcard])
async def get_deck_cards(
    deck_id: int,
    current_user: dict = Depends(get_current_user),
):
    """デッキ内のカードを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        # デッキの所有権確認
        deck = await conn.fetchrow(
            "SELECT * FROM flashcard_decks WHERE id = $1 AND user_id = $2",
            deck_id,
            user_id,
        )
        if not deck:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="デッキが見つかりません"
            )

        rows = await conn.fetch(
            "SELECT * FROM flashcards WHERE deck_id = $1 ORDER BY next_review",
            deck_id,
        )

    return [
        Flashcard(
            id=row["id"],
            front=row["front"],
            back=row["back"],
            easiness=row["easiness"],
            interval=row["interval"],
            repetitions=row["repetitions"],
            next_review=row["next_review"],
        )
        for row in rows
    ]


@router.get("/decks/{deck_id}/review", response_model=list[Flashcard])
async def get_review_cards(
    deck_id: int,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """復習対象のカードを取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        deck = await conn.fetchrow(
            "SELECT * FROM flashcard_decks WHERE id = $1 AND user_id = $2",
            deck_id,
            user_id,
        )
        if not deck:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="デッキが見つかりません"
            )

        rows = await conn.fetch(
            """
            SELECT * FROM flashcards
            WHERE deck_id = $1 AND next_review <= $2
            ORDER BY next_review
            LIMIT $3
            """,
            deck_id,
            datetime.now(UTC),
            limit,
        )

    return [
        Flashcard(
            id=row["id"],
            front=row["front"],
            back=row["back"],
            easiness=row["easiness"],
            interval=row["interval"],
            repetitions=row["repetitions"],
            next_review=row["next_review"],
        )
        for row in rows
    ]


@router.post("/review")
async def submit_review(
    review: ReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """カードの復習結果を送信"""
    user_id = current_user["user_id"]
    pool = get_pool()

    if not 1 <= review.quality <= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="品質は1-5の範囲で指定してください"
        )

    async with pool.acquire() as conn:
        card = await conn.fetchrow("SELECT * FROM flashcards WHERE id = $1", review.card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="カードが見つかりません"
            )

        # SM-2 アルゴリズム
        quality = review.quality
        easiness = card["easiness"]
        interval = card["interval"]
        repetitions = card["repetitions"]

        if quality >= 3:
            if repetitions == 0:
                new_interval = 1
            elif repetitions == 1:
                new_interval = 6
            else:
                new_interval = round(interval * easiness)
            new_repetitions = repetitions + 1
        else:
            new_interval = 1
            new_repetitions = 0

        new_easiness = max(1.3, easiness + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        next_review = datetime.now(UTC) + timedelta(days=new_interval)

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE flashcards
                SET easiness = $2, interval = $3, repetitions = $4, next_review = $5
                WHERE id = $1
                """,
                review.card_id,
                new_easiness,
                new_interval,
                new_repetitions,
                next_review,
            )

            await conn.execute(
                """
                INSERT INTO flashcard_reviews (card_id, user_id, quality)
                VALUES ($1, $2, $3)
                """,
                review.card_id,
                user_id,
                quality,
            )

    return {
        "card_id": review.card_id,
        "new_easiness": round(new_easiness, 2),
        "new_interval": new_interval,
        "next_review": next_review.isoformat(),
    }


@router.get("/decks/{deck_id}/stats", response_model=DeckStats)
async def get_deck_stats(
    deck_id: int,
    current_user: dict = Depends(get_current_user),
):
    """デッキの統計を取得"""
    user_id = current_user["user_id"]
    pool = get_pool()

    async with pool.acquire() as conn:
        deck = await conn.fetchrow(
            "SELECT * FROM flashcard_decks WHERE id = $1 AND user_id = $2",
            deck_id,
            user_id,
        )
        if not deck:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="デッキが見つかりません"
            )

        total = await conn.fetchval("SELECT COUNT(*) FROM flashcards WHERE deck_id = $1", deck_id)
        mastered = await conn.fetchval(
            "SELECT COUNT(*) FROM flashcards WHERE deck_id = $1 AND interval >= 21",
            deck_id,
        )
        learning = await conn.fetchval(
            "SELECT COUNT(*) FROM flashcards WHERE deck_id = $1 AND interval > 0 AND interval < 21",
            deck_id,
        )

    return DeckStats(
        deck_id=deck_id,
        name=deck["name"],
        total=total,
        mastered=mastered,
        learning=learning,
        new=total - mastered - learning,
    )
