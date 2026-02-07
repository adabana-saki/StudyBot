"""API基本テスト"""


def test_root(client):
    """ルートエンドポイント"""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "StudyBot API"
    assert data["version"] == "2.0.0"


def test_health(client):
    """ヘルスチェック"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_stats_unauthorized(client):
    """認証なしでアクセス拒否"""
    resp = client.get("/api/stats/me")
    assert resp.status_code == 403


def test_stats_me(client, auth_headers, mock_pool):
    """自分の統計を取得"""
    _, conn = mock_pool

    # モックDB応答
    conn.fetchrow.side_effect = [
        {"xp": 500, "level": 3, "streak_days": 5},  # user_levels
        {"balance": 100},  # virtual_currency
    ]
    conn.fetchval.return_value = 2  # rank

    resp = client.get("/api/stats/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["xp"] == 500
    assert data["level"] == 3
    assert data["coins"] == 100
    assert data["rank"] == 2


def test_achievements_all(client, mock_pool):
    """全実績を取得"""
    _, conn = mock_pool
    conn.fetch.return_value = [
        {
            "id": 1,
            "key": "first_study",
            "name": "初学者",
            "description": "初めて学習を記録した",
            "emoji": "📖",
            "category": "study",
            "target_value": 1,
            "reward_coins": 50,
        }
    ]

    resp = client.get("/api/achievements/all")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["key"] == "first_study"


def test_wellness_me(client, auth_headers, mock_pool):
    """ウェルネスログ取得"""
    _, conn = mock_pool
    conn.fetch.return_value = []

    resp = client.get("/api/wellness/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_flashcard_decks(client, auth_headers, mock_pool):
    """デッキ一覧取得"""
    _, conn = mock_pool
    conn.fetch.return_value = []

    resp = client.get("/api/flashcards/decks", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
