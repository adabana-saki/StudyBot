"""フラッシュカード DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FlashcardRepository(BaseRepository):
    """フラッシュカードのCRUD"""

    async def create_deck(self, user_id: int, name: str, description: str = "") -> dict:
        """デッキを作成"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO flashcard_decks (user_id, name, description)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                user_id,
                name,
                description,
            )
        return dict(row)

    async def get_user_decks(self, user_id: int) -> list[dict]:
        """ユーザーのデッキ一覧を取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM flashcard_decks
                WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                user_id,
            )
        return [dict(row) for row in rows]

    async def get_deck(self, deck_id: int) -> dict | None:
        """デッキを1件取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM flashcard_decks WHERE id = $1",
                deck_id,
            )
        return dict(row) if row else None

    async def get_deck_by_name(self, user_id: int, name: str) -> dict | None:
        """ユーザーのデッキを名前で取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM flashcard_decks
                WHERE user_id = $1 AND name = $2
                """,
                user_id,
                name,
            )
        return dict(row) if row else None

    async def delete_deck(self, deck_id: int, user_id: int) -> bool:
        """デッキを削除"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM flashcard_decks WHERE id = $1 AND user_id = $2",
                deck_id,
                user_id,
            )
        return result != "DELETE 0"

    async def add_card(self, deck_id: int, front: str, back: str) -> dict:
        """カードを追加し、デッキのカード数を更新"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO flashcards (deck_id, front, back)
                    VALUES ($1, $2, $3)
                    RETURNING *
                    """,
                    deck_id,
                    front,
                    back,
                )
                await conn.execute(
                    """
                    UPDATE flashcard_decks
                    SET card_count = card_count + 1
                    WHERE id = $1
                    """,
                    deck_id,
                )
        return dict(row)

    async def get_cards_for_review(self, deck_id: int, limit: int = 10) -> list[dict]:
        """復習対象のカードを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM flashcards
                WHERE deck_id = $1 AND next_review <= $2
                ORDER BY next_review ASC
                LIMIT $3
                """,
                deck_id,
                datetime.now(UTC),
                limit,
            )
        return [dict(row) for row in rows]

    async def get_deck_cards(self, deck_id: int) -> list[dict]:
        """デッキの全カードを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM flashcards
                WHERE deck_id = $1
                ORDER BY created_at ASC
                """,
                deck_id,
            )
        return [dict(row) for row in rows]

    async def update_card_schedule(
        self,
        card_id: int,
        easiness: float,
        interval: int,
        repetitions: int,
        next_review: datetime,
    ) -> None:
        """カードのスケジュールを更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE flashcards
                SET easiness = $2, interval = $3, repetitions = $4, next_review = $5
                WHERE id = $1
                """,
                card_id,
                easiness,
                interval,
                repetitions,
                next_review,
            )

    async def add_review(self, card_id: int, user_id: int, quality: int) -> None:
        """復習記録を追加"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO flashcard_reviews (card_id, user_id, quality)
                VALUES ($1, $2, $3)
                """,
                card_id,
                user_id,
                quality,
            )

    async def get_deck_stats(self, deck_id: int) -> dict:
        """デッキの統計を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE interval >= 21) AS mastered,
                    COUNT(*) FILTER (WHERE interval > 0 AND interval < 21) AS learning,
                    COUNT(*) FILTER (WHERE interval = 0) AS new
                FROM flashcards
                WHERE deck_id = $1
                """,
                deck_id,
            )
        return dict(row) if row else {"total": 0, "mastered": 0, "learning": 0, "new": 0}
