"""フラッシュカードのテスト"""

from datetime import UTC, datetime

import pytest

from studybot.managers.flashcard_manager import FlashcardManager


@pytest.fixture
def flashcard_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = FlashcardManager(pool)
    return manager, conn


class TestSM2Algorithm:
    """SM-2アルゴリズムのテスト"""

    def test_sm2_quality_3_first_review(self):
        """quality >= 3 で初回復習"""
        result = FlashcardManager.sm2_algorithm(quality=3, easiness=2.5, interval=0, repetitions=0)
        assert result["interval"] == 1
        assert result["repetitions"] == 1
        assert result["easiness"] == pytest.approx(2.36, abs=0.01)

    def test_sm2_quality_3_second_review(self):
        """quality >= 3 で2回目復習"""
        result = FlashcardManager.sm2_algorithm(quality=3, easiness=2.5, interval=1, repetitions=1)
        assert result["interval"] == 6
        assert result["repetitions"] == 2

    def test_sm2_quality_3_third_review(self):
        """quality >= 3 で3回目以降"""
        result = FlashcardManager.sm2_algorithm(quality=4, easiness=2.5, interval=6, repetitions=2)
        assert result["interval"] == round(6 * 2.5)
        assert result["repetitions"] == 3

    def test_sm2_quality_5_perfect(self):
        """quality 5 で完璧な回答"""
        result = FlashcardManager.sm2_algorithm(quality=5, easiness=2.5, interval=6, repetitions=2)
        assert result["interval"] == round(6 * 2.5)
        assert result["repetitions"] == 3
        assert result["easiness"] == pytest.approx(2.6, abs=0.01)

    def test_sm2_quality_below_3_reset(self):
        """quality < 3 でリセット"""
        result = FlashcardManager.sm2_algorithm(quality=2, easiness=2.5, interval=10, repetitions=5)
        assert result["interval"] == 1
        assert result["repetitions"] == 0

    def test_sm2_quality_1_worst(self):
        """quality 1 で最悪の回答"""
        result = FlashcardManager.sm2_algorithm(quality=1, easiness=2.5, interval=10, repetitions=5)
        assert result["interval"] == 1
        assert result["repetitions"] == 0
        # easiness下限チェック
        assert result["easiness"] >= 1.3

    def test_sm2_easiness_minimum(self):
        """easinessの下限は1.3"""
        result = FlashcardManager.sm2_algorithm(quality=1, easiness=1.3, interval=1, repetitions=0)
        assert result["easiness"] >= 1.3

    def test_sm2_quality_4_good(self):
        """quality 4 で良い回答"""
        result = FlashcardManager.sm2_algorithm(quality=4, easiness=2.5, interval=0, repetitions=0)
        assert result["interval"] == 1
        assert result["repetitions"] == 1
        assert result["easiness"] == pytest.approx(2.5, abs=0.01)


@pytest.mark.asyncio
async def test_create_deck(flashcard_manager):
    """デッキ作成テスト"""
    manager, conn = flashcard_manager

    conn.execute.return_value = None
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "name": "英単語",
        "description": "",
        "card_count": 0,
        "created_at": datetime.now(UTC),
    }

    result = await manager.create_deck(user_id=123, username="Test", name="英単語")

    assert result["name"] == "英単語"
    assert result["user_id"] == 123


@pytest.mark.asyncio
async def test_add_card_existing_deck(flashcard_manager):
    """既存デッキへのカード追加テスト"""
    manager, conn = flashcard_manager

    conn.execute.return_value = None
    # get_deck_by_name でデッキが見つかる
    conn.fetchrow.side_effect = [
        # get_deck_by_name
        {
            "id": 1,
            "user_id": 123,
            "name": "英単語",
            "description": "",
            "card_count": 2,
            "created_at": datetime.now(UTC),
        },
        # add_card
        {
            "id": 10,
            "deck_id": 1,
            "front": "apple",
            "back": "りんご",
            "easiness": 2.5,
            "interval": 0,
            "repetitions": 0,
            "next_review": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        },
    ]

    result = await manager.add_card(
        user_id=123, username="Test", deck_name="英単語", front="apple", back="りんご"
    )

    assert result["card"]["front"] == "apple"
    assert result["deck"]["name"] == "英単語"


@pytest.mark.asyncio
async def test_add_card_new_deck(flashcard_manager):
    """新規デッキ自動作成でカード追加テスト"""
    manager, conn = flashcard_manager

    conn.execute.return_value = None
    conn.fetchrow.side_effect = [
        # get_deck_by_name: デッキが見つからない
        None,
        # create_deck
        {
            "id": 2,
            "user_id": 123,
            "name": "数学",
            "description": "",
            "card_count": 0,
            "created_at": datetime.now(UTC),
        },
        # add_card
        {
            "id": 11,
            "deck_id": 2,
            "front": "1+1",
            "back": "2",
            "easiness": 2.5,
            "interval": 0,
            "repetitions": 0,
            "next_review": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        },
    ]

    result = await manager.add_card(
        user_id=123, username="Test", deck_name="数学", front="1+1", back="2"
    )

    assert result["card"]["front"] == "1+1"
    assert result["deck"]["name"] == "数学"


@pytest.mark.asyncio
async def test_get_review_cards_deck_not_found(flashcard_manager):
    """存在しないデッキの復習"""
    manager, conn = flashcard_manager

    conn.fetchrow.return_value = None

    result = await manager.get_review_cards(user_id=123, deck_name="不明")

    assert "error" in result


@pytest.mark.asyncio
async def test_get_review_cards_no_cards(flashcard_manager):
    """復習カードがない場合"""
    manager, conn = flashcard_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "name": "英単語",
        "description": "",
        "card_count": 5,
        "created_at": datetime.now(UTC),
    }
    conn.fetch.return_value = []

    result = await manager.get_review_cards(user_id=123, deck_name="英単語")

    assert result["cards"] == []
    assert "message" in result


@pytest.mark.asyncio
async def test_review_card_with_state(flashcard_manager):
    """状態付きカード復習テスト"""
    manager, conn = flashcard_manager

    conn.execute.return_value = None

    result = await manager.review_card_with_state(
        card_id=1,
        user_id=123,
        quality=4,
        easiness=2.5,
        interval=0,
        repetitions=0,
    )

    assert "easiness" in result
    assert result["interval"] == 1
    assert result["repetitions"] == 1
    assert "next_review" in result


@pytest.mark.asyncio
async def test_review_card_invalid_quality(flashcard_manager):
    """不正な評価値"""
    manager, conn = flashcard_manager

    result = await manager.review_card(card_id=1, user_id=123, quality=6)

    assert "error" in result


@pytest.mark.asyncio
async def test_get_user_stats(flashcard_manager):
    """ユーザー統計テスト"""
    manager, conn = flashcard_manager

    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123,
            "name": "英単語",
            "description": "",
            "card_count": 10,
            "created_at": datetime.now(UTC),
        },
    ]
    conn.fetchrow.return_value = {
        "total": 10,
        "mastered": 3,
        "learning": 5,
        "new": 2,
    }

    result = await manager.get_user_stats(user_id=123)

    assert len(result) == 1
    assert result[0]["deck"]["name"] == "英単語"
    assert result[0]["stats"]["total"] == 10
    assert result[0]["stats"]["mastered"] == 3
