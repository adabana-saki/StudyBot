"""API包括テスト - 全エンドポイント"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from api.auth.jwt_handler import create_refresh_token


# ============================================================
# Global / Root
# ============================================================


class TestGlobal:
    """ルート & ヘルスチェック"""

    def test_root(self, client):
        """ルートエンドポイント"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "StudyBot API"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"

    def test_health(self, client):
        """ヘルスチェック"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_cors_headers(self, client):
        """CORS: プリフライトで正しいヘッダーが返る"""
        resp = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers


# ============================================================
# Auth
# ============================================================


class TestAuth:
    """認証エンドポイント"""

    def test_discord_login_redirect(self, client):
        """Discord OAuth2 リダイレクト"""
        resp = client.get(
            "/api/auth/discord",
            follow_redirects=False,
        )
        assert resp.status_code == 307
        location = resp.headers["location"]
        assert "discord.com/api/oauth2/authorize" in location
        assert "response_type=code" in location

    def test_refresh_token_success(self, client, mock_pool):
        """リフレッシュトークン: 正常"""
        _, conn = mock_pool
        refresh = create_refresh_token(123456789)
        conn.fetchrow.return_value = {"username": "TestUser"}

        resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client):
        """リフレッシュトークン: 不正トークン"""
        resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.jwt.token"},
        )
        assert resp.status_code == 401

    def test_refresh_token_wrong_type(self, client, test_token):
        """リフレッシュトークン: accessトークンを渡した場合"""
        resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": test_token},
        )
        # accessトークンにはtype=refreshが無いので拒否
        assert resp.status_code == 401


# ============================================================
# Stats
# ============================================================


class TestStats:
    """統計エンドポイント"""

    def test_stats_me_success(self, client, auth_headers, mock_pool):
        """自分のプロフィール取得: 正常"""
        _, conn = mock_pool
        conn.fetchrow.side_effect = [
            {"username": "TestUser", "avatar_url": ""},
            {"xp": 1500, "level": 7, "streak_days": 12},
            {"balance": 350},
        ]
        conn.fetchval.return_value = 3

        resp = client.get("/api/stats/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == 123456789
        assert data["username"] == "TestUser"
        assert data["xp"] == 1500
        assert data["level"] == 7
        assert data["streak_days"] == 12
        assert data["coins"] == 350
        assert data["rank"] == 3

    def test_stats_me_unauthorized(self, client):
        """認証なしでアクセス拒否"""
        resp = client.get("/api/stats/me")
        assert resp.status_code in (401, 403)

    def test_stats_me_no_data(self, client, auth_headers, mock_pool):
        """プロフィール取得: DB未登録ユーザー"""
        _, conn = mock_pool
        conn.fetchrow.side_effect = [None, None, None]
        conn.fetchval.return_value = 0

        resp = client.get("/api/stats/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["xp"] == 0
        assert data["level"] == 1
        assert data["streak_days"] == 0
        assert data["coins"] == 0

    def test_stats_me_study_weekly(self, client, auth_headers, mock_pool):
        """学習統計: weekly"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "total_minutes": 420,
            "session_count": 14,
            "avg_minutes": 30.0,
        }

        resp = client.get(
            "/api/stats/me/study?period=weekly",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_minutes"] == 420
        assert data["session_count"] == 14
        assert data["avg_minutes"] == 30.0
        assert data["period"] == "weekly"

    def test_stats_me_study_monthly(self, client, auth_headers, mock_pool):
        """学習統計: monthly"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "total_minutes": 1800,
            "session_count": 60,
            "avg_minutes": 30.0,
        }

        resp = client.get(
            "/api/stats/me/study?period=monthly",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_minutes"] == 1800
        assert data["period"] == "monthly"

    def test_stats_me_study_all_time(self, client, auth_headers, mock_pool):
        """学習統計: all_time"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "total_minutes": 10000,
            "session_count": 300,
            "avg_minutes": 33.33,
        }

        resp = client.get(
            "/api/stats/me/study?period=all_time",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_minutes"] == 10000
        assert data["period"] == "all_time"

    def test_stats_me_daily(self, client, auth_headers, mock_pool):
        """日別学習時間を取得"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "day": "2025-01-10",
                "total_minutes": 60,
            },
            {
                "day": "2025-01-11",
                "total_minutes": 90,
            },
            {
                "day": "2025-01-12",
                "total_minutes": 45,
            },
        ]

        resp = client.get(
            "/api/stats/me/daily?days=7",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["day"] == "2025-01-10"
        assert data[0]["total_minutes"] == 60
        assert data[2]["total_minutes"] == 45

    def test_stats_me_daily_empty(self, client, auth_headers, mock_pool):
        """日別学習時間: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get("/api/stats/me/daily", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ============================================================
# Leaderboard
# ============================================================

GUILD_ID = 987654321


class TestLeaderboard:
    """リーダーボードエンドポイント"""

    def test_leaderboard_default(self, client, mock_pool):
        """デフォルト(xp, all_time)でリーダーボード取得"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "user_id": 1,
                "username": "Alice",
                "value": 5000,
                "level": 10,
            },
            {
                "user_id": 2,
                "username": "Bob",
                "value": 3000,
                "level": 7,
            },
        ]

        resp = client.get(f"/api/leaderboard/{GUILD_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "xp"
        assert data["period"] == "all_time"
        assert len(data["entries"]) == 2
        assert data["entries"][0]["rank"] == 1
        assert data["entries"][0]["username"] == "Alice"
        assert data["entries"][0]["value"] == 5000
        assert data["entries"][1]["rank"] == 2

    def test_leaderboard_by_category_study(self, client, mock_pool):
        """カテゴリ: study_time"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "user_id": 1,
                "username": "Alice",
                "value": 1200,
                "level": 10,
            },
        ]

        resp = client.get(f"/api/leaderboard/{GUILD_ID}?category=study")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "study"

    def test_leaderboard_by_category_tasks(self, client, mock_pool):
        """カテゴリ: tasks"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "user_id": 3,
                "username": "Charlie",
                "value": 42,
                "level": 5,
            },
        ]

        resp = client.get(f"/api/leaderboard/{GUILD_ID}?category=tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "tasks"
        assert data["entries"][0]["value"] == 42

    def test_leaderboard_by_period_weekly(self, client, mock_pool):
        """期間: weekly"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(f"/api/leaderboard/{GUILD_ID}?category=xp&period=weekly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "weekly"

    def test_leaderboard_by_period_monthly(self, client, mock_pool):
        """期間: monthly"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(f"/api/leaderboard/{GUILD_ID}?category=xp&period=monthly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "monthly"

    def test_leaderboard_empty(self, client, mock_pool):
        """リーダーボード: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(f"/api/leaderboard/{GUILD_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []

    def test_leaderboard_invalid_category(self, client, mock_pool):
        """無効なカテゴリ"""
        resp = client.get(f"/api/leaderboard/{GUILD_ID}?category=invalid")
        assert resp.status_code == 422


# ============================================================
# Achievements
# ============================================================


class TestAchievements:
    """実績エンドポイント"""

    def test_achievements_all(self, client, mock_pool):
        """全実績を取得"""
        _, conn = mock_pool
        conn.fetchval.return_value = 2
        conn.fetch.return_value = [
            {
                "id": 1,
                "key": "first_study",
                "name": "初学者",
                "description": "初めて学習を記録した",
                "emoji": "a]",
                "category": "study",
                "target_value": 1,
                "reward_coins": 50,
            },
            {
                "id": 2,
                "key": "streak_7",
                "name": "習慣化",
                "description": "7日連続学習",
                "emoji": "b]",
                "category": "streak",
                "target_value": 7,
                "reward_coins": 100,
            },
        ]

        resp = client.get("/api/achievements/all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["key"] == "first_study"
        assert data["items"][0]["reward_coins"] == 50
        assert data["items"][1]["key"] == "streak_7"
        assert data["items"][1]["target_value"] == 7

    def test_achievements_me_with_progress(self, client, auth_headers, mock_pool):
        """自分の実績: 進捗あり"""
        _, conn = mock_pool
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        conn.fetchval.return_value = 2
        conn.fetch.return_value = [
            {
                "id": 1,
                "key": "first_study",
                "name": "初学者",
                "description": "初めて学習を記録した",
                "emoji": "a]",
                "category": "study",
                "target_value": 1,
                "reward_coins": 50,
                "progress": 1,
                "unlocked": True,
                "unlocked_at": now,
            },
            {
                "id": 2,
                "key": "streak_7",
                "name": "習慣化",
                "description": "7日連続学習",
                "emoji": "b]",
                "category": "streak",
                "target_value": 7,
                "reward_coins": 100,
                "progress": 3,
                "unlocked": False,
                "unlocked_at": None,
            },
        ]

        resp = client.get("/api/achievements/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        assert len(items) == 2

        # 解除済み実績
        assert items[0]["unlocked"] is True
        assert items[0]["progress"] == 1
        assert items[0]["achievement"]["key"] == "first_study"
        assert items[0]["unlocked_at"] is not None

        # 未解除実績
        assert items[1]["unlocked"] is False
        assert items[1]["progress"] == 3
        assert items[1]["unlocked_at"] is None

    def test_achievements_me_empty(self, client, auth_headers, mock_pool):
        """自分の実績: データなし"""
        _, conn = mock_pool
        conn.fetchval.return_value = 0
        conn.fetch.return_value = []

        resp = client.get("/api/achievements/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_achievements_me_unauthorized(self, client):
        """自分の実績: 認証なし"""
        resp = client.get("/api/achievements/me")
        assert resp.status_code in (401, 403)


# ============================================================
# Flashcards
# ============================================================


class TestFlashcards:
    """フラッシュカードエンドポイント"""

    _NOW = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

    def _deck_row(self, **overrides):
        """テスト用デッキ行を作成"""
        base = {
            "id": 1,
            "name": "Python基礎",
            "description": "Python基礎文法",
            "card_count": 20,
            "created_at": self._NOW,
            "user_id": 123456789,
        }
        base.update(overrides)
        return base

    def _card_row(self, **overrides):
        """テスト用カード行を作成"""
        base = {
            "id": 1,
            "front": "リストの作成方法は?",
            "back": "list() or []",
            "easiness": 2.5,
            "interval": 1,
            "repetitions": 0,
            "next_review": self._NOW,
            "deck_id": 1,
        }
        base.update(overrides)
        return base

    def test_flashcard_decks_list(self, client, auth_headers, mock_pool):
        """デッキ一覧取得: データあり"""
        _, conn = mock_pool
        conn.fetchval.return_value = 2
        conn.fetch.return_value = [
            self._deck_row(),
            self._deck_row(
                id=2,
                name="英単語",
                description="TOEIC頻出",
                card_count=50,
            ),
        ]

        resp = client.get("/api/flashcards/decks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        items = data["items"]
        assert len(items) == 2
        assert items[0]["name"] == "Python基礎"
        assert items[0]["card_count"] == 20
        assert items[1]["name"] == "英単語"

    def test_flashcard_decks_empty(self, client, auth_headers, mock_pool):
        """デッキ一覧取得: 空"""
        _, conn = mock_pool
        conn.fetchval.return_value = 0
        conn.fetch.return_value = []

        resp = client.get("/api/flashcards/decks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_flashcard_deck_cards(self, client, auth_headers, mock_pool):
        """デッキ内のカード取得"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._deck_row()
        conn.fetch.return_value = [
            self._card_row(),
            self._card_row(
                id=2,
                front="辞書の作成方法は?",
                back="dict() or {}",
            ),
        ]

        resp = client.get(
            "/api/flashcards/decks/1/cards",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["front"] == "リストの作成方法は?"
        assert data[1]["front"] == "辞書の作成方法は?"

    def test_flashcard_deck_not_found(self, client, auth_headers, mock_pool):
        """存在しないデッキ"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.get(
            "/api/flashcards/decks/999/cards",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_flashcard_review_cards(self, client, auth_headers, mock_pool):
        """復習対象カードを取得"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._deck_row()
        conn.fetch.return_value = [
            self._card_row(),
            self._card_row(id=2, front="Q2", back="A2"),
        ]

        resp = client.get(
            "/api/flashcards/decks/1/review",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["easiness"] == 2.5
        assert data[0]["repetitions"] == 0

    def test_flashcard_review_deck_not_found(self, client, auth_headers, mock_pool):
        """復習: 存在しないデッキ"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.get(
            "/api/flashcards/decks/999/review",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_submit_review_success(self, client, auth_headers, mock_pool):
        """カード復習送信: 正常 (quality >= 3)"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._card_row(easiness=2.5, interval=1, repetitions=0)
        conn.execute = AsyncMock()

        resp = client.post(
            "/api/flashcards/review",
            json={"card_id": 1, "quality": 4},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["card_id"] == 1
        assert data["new_interval"] == 1
        assert "new_easiness" in data
        assert "next_review" in data

    def test_submit_review_low_quality(self, client, auth_headers, mock_pool):
        """カード復習送信: quality < 3 でリセット"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._card_row(easiness=2.5, interval=6, repetitions=2)
        conn.execute = AsyncMock()

        resp = client.post(
            "/api/flashcards/review",
            json={"card_id": 1, "quality": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_interval"] == 1

    def test_submit_review_invalid_quality(self, client, auth_headers, mock_pool):
        """カード復習送信: 品質範囲外（Pydantic検証で422）"""
        _, conn = mock_pool

        resp = client.post(
            "/api/flashcards/review",
            json={"card_id": 1, "quality": 6},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_submit_review_card_not_found(self, client, auth_headers, mock_pool):
        """カード復習送信: カード不在"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.post(
            "/api/flashcards/review",
            json={"card_id": 999, "quality": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_deck_stats(self, client, auth_headers, mock_pool):
        """デッキ統計を取得"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._deck_row()
        conn.fetchval.side_effect = [
            30,  # total
            5,  # mastered (interval >= 21)
            15,  # learning (0 < interval < 21)
        ]

        resp = client.get(
            "/api/flashcards/decks/1/stats",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deck_id"] == 1
        assert data["name"] == "Python基礎"
        assert data["total"] == 30
        assert data["mastered"] == 5
        assert data["learning"] == 15
        assert data["new"] == 10  # 30 - 5 - 15

    def test_deck_stats_not_found(self, client, auth_headers, mock_pool):
        """デッキ統計: デッキ不在"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.get(
            "/api/flashcards/decks/999/stats",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ============================================================
# Wellness
# ============================================================


class TestWellness:
    """ウェルネスエンドポイント"""

    _NOW = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

    def test_wellness_me_get(self, client, auth_headers, mock_pool):
        """ウェルネスログ取得: データあり"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "mood": 4,
                "energy": 3,
                "stress": 2,
                "note": "調子良い",
                "logged_at": self._NOW,
            },
            {
                "id": 2,
                "mood": 3,
                "energy": 4,
                "stress": 3,
                "note": "",
                "logged_at": self._NOW,
            },
        ]

        resp = client.get("/api/wellness/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["mood"] == 4
        assert data[0]["note"] == "調子良い"
        assert data[1]["stress"] == 3

    def test_wellness_me_get_empty(self, client, auth_headers, mock_pool):
        """ウェルネスログ取得: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get("/api/wellness/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_wellness_me_post(self, client, auth_headers, mock_pool):
        """ウェルネス記録: 正常"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": 10,
            "mood": 4,
            "energy": 3,
            "stress": 2,
            "note": "勉強後",
            "logged_at": self._NOW,
        }

        resp = client.post(
            "/api/wellness/me",
            json={
                "mood": 4,
                "energy": 3,
                "stress": 2,
                "note": "勉強後",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 10
        assert data["mood"] == 4
        assert data["energy"] == 3
        assert data["stress"] == 2
        assert data["note"] == "勉強後"

    def test_wellness_me_post_no_note(self, client, auth_headers, mock_pool):
        """ウェルネス記録: メモなし"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": 11,
            "mood": 3,
            "energy": 3,
            "stress": 3,
            "note": "",
            "logged_at": self._NOW,
        }

        resp = client.post(
            "/api/wellness/me",
            json={"mood": 3, "energy": 3, "stress": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["note"] == ""

    def test_wellness_me_post_invalid_range(self, client, auth_headers, mock_pool):
        """ウェルネス記録: 範囲外の値（Pydantic検証で422）"""
        _, conn = mock_pool

        resp = client.post(
            "/api/wellness/me",
            json={"mood": 6, "energy": 3, "stress": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_wellness_averages(self, client, auth_headers, mock_pool):
        """ウェルネス平均値を取得"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "avg_mood": 3.5,
            "avg_energy": 3.2,
            "avg_stress": 2.8,
        }

        resp = client.get(
            "/api/wellness/me/averages?days=7",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_mood"] == 3.5
        assert data["avg_energy"] == 3.2
        assert data["avg_stress"] == 2.8
        assert data["days"] == 7

    def test_wellness_averages_default_days(self, client, auth_headers, mock_pool):
        """ウェルネス平均値: デフォルト日数"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "avg_mood": 4.0,
            "avg_energy": 4.0,
            "avg_stress": 1.0,
        }

        resp = client.get(
            "/api/wellness/me/averages",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["days"] == 7

    def test_wellness_unauthorized(self, client):
        """ウェルネス: 認証なし"""
        resp = client.get("/api/wellness/me")
        assert resp.status_code in (401, 403)

        resp = client.post(
            "/api/wellness/me",
            json={"mood": 3, "energy": 3, "stress": 3},
        )
        assert resp.status_code in (401, 403)

        resp = client.get("/api/wellness/me/averages")
        assert resp.status_code in (401, 403)
