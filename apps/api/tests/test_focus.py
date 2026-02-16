"""フォーカス/チャレンジAPIのテスト"""

import json
from datetime import UTC, datetime, timedelta


def test_get_focus_status_no_session(client, auth_headers, mock_pool):
    """アクティブセッションなしでステータス取得"""
    _, conn = mock_pool
    conn.fetchrow.return_value = None

    res = client.get("/api/focus/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() is None


def test_get_focus_status_active(client, auth_headers, mock_pool):
    """アクティブセッションありでステータス取得"""
    _, conn = mock_pool

    started = datetime.now(UTC) - timedelta(minutes=10)
    session_row = {
        "id": 1,
        "user_id": 123456789,
        "lock_type": "lock",
        "duration_minutes": 60,
        "coins_bet": 20,
        "unlock_level": 1,
        "challenge_mode": "math",
        "state": "active",
        "started_at": started,
        "ended_at": None,
    }
    settings_row = {
        "block_categories": ["sns", "games"],
        "block_message": "頑張って！",
    }

    conn.fetchrow.side_effect = [session_row, settings_row]

    res = client.get("/api/focus/status", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == 1
    assert data["challenge_mode"] == "math"
    assert data["block_categories"] == ["sns", "games"]
    assert data["block_message"] == "頑張って！"
    assert data["remaining_seconds"] > 0


def test_start_focus_with_challenge(client, auth_headers, mock_pool):
    """チャレンジモード付きでセッション開始"""
    _, conn = mock_pool

    conn.fetchrow.side_effect = [
        None,  # no active session
        {  # INSERT RETURNING
            "id": 2,
            "user_id": 123456789,
            "lock_type": "lock",
            "duration_minutes": 30,
            "coins_bet": 0,
            "unlock_level": 1,
            "challenge_mode": "math",
            "state": "active",
            "started_at": datetime.now(UTC),
            "ended_at": None,
        },
    ]

    res = client.post(
        "/api/focus/start",
        headers=auth_headers,
        json={"duration": 30, "unlock_level": 1, "coins_bet": 0, "challenge_mode": "math"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["challenge_mode"] == "math"
    assert data["session_id"] == 2


def test_start_focus_invalid_challenge_mode(client, auth_headers, mock_pool):
    """無効なチャレンジモードでエラー"""
    _, conn = mock_pool
    conn.fetchrow.return_value = None  # no existing session

    res = client.post(
        "/api/focus/start",
        headers=auth_headers,
        json={"duration": 30, "unlock_level": 1, "coins_bet": 0, "challenge_mode": "invalid"},
    )
    assert res.status_code == 400


def test_generate_math_challenge(client, auth_headers, mock_pool):
    """計算チャレンジ生成"""
    _, conn = mock_pool

    # Active session
    conn.fetchrow.side_effect = [
        {"id": 1, "challenge_mode": "math"},  # session
        {"id": 10},  # INSERT RETURNING (challenge_attempts)
    ]

    res = client.post(
        "/api/focus/challenge/generate",
        headers=auth_headers,
        json={"challenge_type": "math", "difficulty": 1},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["challenge_type"] == "math"
    assert data["challenge_id"] == 10
    assert len(data["problems"]) == 3
    # Answer should NOT be included in client response
    for p in data["problems"]:
        assert "answer" not in p
        assert "expression" in p


def test_generate_typing_challenge(client, auth_headers, mock_pool):
    """タイピングチャレンジ生成"""
    _, conn = mock_pool

    conn.fetchrow.side_effect = [
        {"id": 1, "challenge_mode": "typing"},  # session
        {"id": 11},  # INSERT RETURNING
    ]

    res = client.post(
        "/api/focus/challenge/generate",
        headers=auth_headers,
        json={"challenge_type": "typing", "difficulty": 2},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["challenge_type"] == "typing"
    assert len(data["problems"]) == 2
    for p in data["problems"]:
        assert isinstance(p, str)


def test_generate_challenge_no_session(client, auth_headers, mock_pool):
    """セッションなしでチャレンジ生成 → 404"""
    _, conn = mock_pool
    conn.fetchrow.return_value = None

    res = client.post(
        "/api/focus/challenge/generate",
        headers=auth_headers,
        json={"challenge_type": "math", "difficulty": 1},
    )
    assert res.status_code == 404


def test_verify_math_challenge_correct(client, auth_headers, mock_pool):
    """計算チャレンジ検証 - 正解"""
    _, conn = mock_pool

    problems = [
        {"expression": "5 + 3", "answer": 8},
        {"expression": "10 - 4", "answer": 6},
        {"expression": "3 * 7", "answer": 21},
    ]

    conn.fetchrow.return_value = {
        "id": 10,
        "user_id": 123456789,
        "session_id": 1,
        "challenge_type": "math",
        "difficulty": 1,
        "problems": json.dumps(problems),
        "answers": "[]",
        "correct": False,
    }
    conn.execute.return_value = None

    res = client.post(
        "/api/focus/challenge/verify",
        headers=auth_headers,
        json={"challenge_id": 10, "answers": [8, 6, 21]},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["correct"] is True
    assert data["score"] == 3
    assert data["total"] == 3
    assert data["dismissed_until"] is not None


def test_verify_math_challenge_wrong(client, auth_headers, mock_pool):
    """計算チャレンジ検証 - 不正解"""
    _, conn = mock_pool

    problems = [
        {"expression": "5 + 3", "answer": 8},
        {"expression": "10 - 4", "answer": 6},
    ]

    conn.fetchrow.return_value = {
        "id": 10,
        "user_id": 123456789,
        "session_id": 1,
        "challenge_type": "math",
        "difficulty": 1,
        "problems": json.dumps(problems),
        "answers": "[]",
        "correct": False,
    }
    conn.execute.return_value = None

    res = client.post(
        "/api/focus/challenge/verify",
        headers=auth_headers,
        json={"challenge_id": 10, "answers": [8, 999]},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["correct"] is False
    assert data["score"] == 1


def test_verify_typing_challenge(client, auth_headers, mock_pool):
    """タイピングチャレンジ検証"""
    _, conn = mock_pool

    phrases = ["集中して学習に取り組みましょう"]

    conn.fetchrow.return_value = {
        "id": 11,
        "user_id": 123456789,
        "session_id": 1,
        "challenge_type": "typing",
        "difficulty": 1,
        "problems": json.dumps(phrases),
        "answers": "[]",
        "correct": False,
    }
    conn.execute.return_value = None

    res = client.post(
        "/api/focus/challenge/verify",
        headers=auth_headers,
        json={"challenge_id": 11, "answers": ["集中して学習に取り組みましょう"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["correct"] is True
    assert data["accuracy"] == 100.0


def test_verify_challenge_not_found(client, auth_headers, mock_pool):
    """存在しないチャレンジID → 404"""
    _, conn = mock_pool
    conn.fetchrow.return_value = None

    res = client.post(
        "/api/focus/challenge/verify",
        headers=auth_headers,
        json={"challenge_id": 999, "answers": [1]},
    )
    assert res.status_code == 404


def test_update_settings_with_challenge(client, auth_headers, mock_pool):
    """チャレンジ設定付きでロック設定更新"""
    _, conn = mock_pool

    existing = {
        "default_unlock_level": 1,
        "default_duration": 60,
        "default_coin_bet": 0,
        "block_categories": [],
        "custom_blocked_urls": [],
        "challenge_mode": "none",
        "challenge_difficulty": 1,
        "block_message": "",
    }

    updated = {
        **existing,
        "challenge_mode": "math",
        "challenge_difficulty": 3,
        "block_message": "集中！",
    }

    conn.fetchrow.side_effect = [existing, updated]

    res = client.put(
        "/api/focus/settings",
        headers=auth_headers,
        json={
            "challenge_mode": "math",
            "challenge_difficulty": 3,
            "block_message": "集中！",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["challenge_mode"] == "math"
    assert data["challenge_difficulty"] == 3
    assert data["block_message"] == "集中！"


def test_update_settings_url_limit(client, auth_headers, mock_pool):
    """カスタムURL50件制限"""
    _, conn = mock_pool

    conn.fetchrow.return_value = None  # no existing settings

    urls = [f"https://example{i}.com" for i in range(51)]
    res = client.put(
        "/api/focus/settings",
        headers=auth_headers,
        json={"custom_blocked_urls": urls},
    )
    assert res.status_code == 400
