"""フラッシュカード ビジネスロジック"""

import logging
from datetime import UTC, datetime, timedelta

from studybot.config.constants import SM2_DEFAULTS
from studybot.repositories.flashcard_repository import FlashcardRepository

logger = logging.getLogger(__name__)


class FlashcardManager:
    """フラッシュカード管理のビジネスロジック"""

    def __init__(self, db_pool) -> None:
        self.repository = FlashcardRepository(db_pool)

    async def create_deck(
        self, user_id: int, username: str, name: str, description: str = ""
    ) -> dict:
        """デッキを作成"""
        await self.repository.ensure_user(user_id, username)
        return await self.repository.create_deck(user_id, name, description)

    async def add_card(
        self, user_id: int, username: str, deck_name: str, front: str, back: str
    ) -> dict:
        """カードを追加（デッキがなければ自動作成）"""
        await self.repository.ensure_user(user_id, username)

        # デッキを名前で検索
        deck = await self.repository.get_deck_by_name(user_id, deck_name)
        if not deck:
            deck = await self.repository.create_deck(user_id, deck_name)

        card = await self.repository.add_card(deck["id"], front, back)
        return {"card": card, "deck": deck}

    async def get_review_cards(self, user_id: int, deck_name: str) -> dict:
        """復習対象のカードを取得"""
        deck = await self.repository.get_deck_by_name(user_id, deck_name)
        if not deck:
            return {"error": f"デッキ「{deck_name}」が見つかりません。"}

        cards = await self.repository.get_cards_for_review(deck["id"])
        if not cards:
            return {"deck": deck, "cards": [], "message": "復習するカードはありません。"}

        return {"deck": deck, "cards": cards}

    async def review_card(self, card_id: int, user_id: int, quality: int) -> dict:
        """カードを復習（SM-2アルゴリズム適用）"""
        if not 1 <= quality <= 5:
            return {"error": "評価は1〜5の範囲で指定してください。"}

        # SM-2アルゴリズムでスケジュール計算
        # カード情報はViewで保持しているため、ここではデフォルト値から計算しない
        # 実際にはViewからeasiness/interval/repetitionsを渡す
        result = self.sm2_algorithm(
            quality=quality,
            easiness=SM2_DEFAULTS["initial_easiness"],
            interval=SM2_DEFAULTS["initial_interval"],
            repetitions=SM2_DEFAULTS["initial_repetitions"],
        )

        next_review = datetime.now(UTC) + timedelta(days=result["interval"])

        await self.repository.update_card_schedule(
            card_id=card_id,
            easiness=result["easiness"],
            interval=result["interval"],
            repetitions=result["repetitions"],
            next_review=next_review,
        )
        await self.repository.add_review(card_id, user_id, quality)

        return {
            "easiness": result["easiness"],
            "interval": result["interval"],
            "repetitions": result["repetitions"],
            "next_review": next_review,
        }

    async def review_card_with_state(
        self,
        card_id: int,
        user_id: int,
        quality: int,
        easiness: float,
        interval: int,
        repetitions: int,
    ) -> dict:
        """カードを復習（現在の状態を使ってSM-2適用）"""
        if not 1 <= quality <= 5:
            return {"error": "評価は1〜5の範囲で指定してください。"}

        result = self.sm2_algorithm(
            quality=quality,
            easiness=easiness,
            interval=interval,
            repetitions=repetitions,
        )

        next_review = datetime.now(UTC) + timedelta(days=result["interval"])

        await self.repository.update_card_schedule(
            card_id=card_id,
            easiness=result["easiness"],
            interval=result["interval"],
            repetitions=result["repetitions"],
            next_review=next_review,
        )
        await self.repository.add_review(card_id, user_id, quality)

        return {
            "easiness": result["easiness"],
            "interval": result["interval"],
            "repetitions": result["repetitions"],
            "next_review": next_review,
        }

    async def get_user_stats(self, user_id: int) -> list[dict]:
        """ユーザーの全デッキ統計を取得"""
        decks = await self.repository.get_user_decks(user_id)
        stats_list = []

        for deck in decks:
            stats = await self.repository.get_deck_stats(deck["id"])
            stats_list.append(
                {
                    "deck": deck,
                    "stats": stats,
                }
            )

        return stats_list

    @staticmethod
    def sm2_algorithm(
        quality: int,
        easiness: float,
        interval: int,
        repetitions: int,
    ) -> dict:
        """SM-2 間隔反復アルゴリズム"""
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

        new_easiness = max(
            SM2_DEFAULTS["min_easiness"],
            easiness + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
        )

        return {
            "easiness": new_easiness,
            "interval": new_interval,
            "repetitions": new_repetitions,
        }
