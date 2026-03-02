"""AppGuard APIのテスト"""

from datetime import UTC, datetime


# === Usage Sync ===


def test_sync_usage(client, auth_headers, mock_pool):
    """使用データの一括同期"""
    _, conn = mock_pool

    res = client.post(
        "/api/focus/app-guard/usage/sync",
        headers=auth_headers,
        json={
            "session_id": 1,
            "entries": [
                {
                    "package_name": "com.twitter.android",
                    "app_name": "Twitter",
                    "foreground_time_ms": 60000,
                    "period_start": "2026-02-20T00:00:00Z",
                    "period_end": "2026-02-20T01:00:00Z",
                },
                {
                    "package_name": "com.instagram.android",
                    "app_name": "Instagram",
                    "foreground_time_ms": 30000,
                    "period_start": "2026-02-20T00:00:00Z",
                    "period_end": "2026-02-20T01:00:00Z",
                },
            ],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["synced"] == 2
    assert conn.execute.call_count == 2


def test_sync_usage_empty(client, auth_headers, mock_pool):
    """空の使用データ同期"""
    res = client.post(
        "/api/focus/app-guard/usage/sync",
        headers=auth_headers,
        json={"session_id": None, "entries": []},
    )
    assert res.status_code == 201
    assert res.json()["synced"] == 0


def test_get_usage_history(client, auth_headers, mock_pool):
    """使用履歴取得（ページネーション）"""
    _, conn = mock_pool

    conn.fetchval.return_value = 2
    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123456789,
            "session_id": 1,
            "package_name": "com.twitter.android",
            "app_name": "Twitter",
            "foreground_time_ms": 60000,
            "period_start": datetime(2026, 2, 20, tzinfo=UTC),
            "period_end": datetime(2026, 2, 20, 1, tzinfo=UTC),
            "synced_at": datetime(2026, 2, 20, 2, tzinfo=UTC),
        },
        {
            "id": 2,
            "user_id": 123456789,
            "session_id": 1,
            "package_name": "com.instagram.android",
            "app_name": "Instagram",
            "foreground_time_ms": 30000,
            "period_start": datetime(2026, 2, 20, tzinfo=UTC),
            "period_end": datetime(2026, 2, 20, 1, tzinfo=UTC),
            "synced_at": datetime(2026, 2, 20, 2, tzinfo=UTC),
        },
    ]

    res = client.get(
        "/api/focus/app-guard/usage?limit=10&offset=0",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["package_name"] == "com.twitter.android"


def test_get_session_usage(client, auth_headers, mock_pool):
    """特定セッションの使用データ"""
    _, conn = mock_pool

    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123456789,
            "session_id": 5,
            "package_name": "com.twitter.android",
            "app_name": "Twitter",
            "foreground_time_ms": 60000,
            "period_start": datetime(2026, 2, 20, tzinfo=UTC),
            "period_end": datetime(2026, 2, 20, 1, tzinfo=UTC),
            "synced_at": datetime(2026, 2, 20, 2, tzinfo=UTC),
        },
    ]

    res = client.get(
        "/api/focus/app-guard/usage/session/5",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["session_id"] == 5


# === Breaches Sync ===


def test_sync_breaches(client, auth_headers, mock_pool):
    """ブリーチイベントの一括同期"""
    _, conn = mock_pool

    res = client.post(
        "/api/focus/app-guard/breaches/sync",
        headers=auth_headers,
        json={
            "session_id": 1,
            "breaches": [
                {
                    "package_name": "com.twitter.android",
                    "app_name": "Twitter",
                    "breach_duration_ms": 5000,
                    "occurred_at": "2026-02-20T10:30:00Z",
                },
            ],
        },
    )
    assert res.status_code == 201
    assert res.json()["synced"] == 1


def test_get_breach_history(client, auth_headers, mock_pool):
    """ブリーチ履歴取得"""
    _, conn = mock_pool

    conn.fetchval.return_value = 1
    conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 123456789,
            "session_id": 1,
            "package_name": "com.twitter.android",
            "app_name": "Twitter",
            "breach_duration_ms": 5000,
            "occurred_at": datetime(2026, 2, 20, 10, 30, tzinfo=UTC),
            "created_at": datetime(2026, 2, 20, 10, 31, tzinfo=UTC),
        },
    ]

    res = client.get(
        "/api/focus/app-guard/breaches?limit=10&offset=0",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["breach_duration_ms"] == 5000


# === Blocked Apps ===


def test_get_blocked_apps_empty(client, auth_headers, mock_pool):
    """ブロックアプリ一覧（空）"""
    _, conn = mock_pool
    conn.fetch.return_value = []

    res = client.get("/api/focus/app-guard/blocked-apps", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_add_blocked_app(client, auth_headers, mock_pool):
    """ブロックアプリ追加"""
    _, conn = mock_pool

    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123456789,
        "package_name": "com.twitter.android",
        "app_name": "Twitter",
        "category": "social",
        "added_at": datetime(2026, 2, 20, tzinfo=UTC),
    }

    res = client.post(
        "/api/focus/app-guard/blocked-apps",
        headers=auth_headers,
        json={
            "package_name": "com.twitter.android",
            "app_name": "Twitter",
            "category": "social",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["package_name"] == "com.twitter.android"
    assert data["category"] == "social"


def test_add_blocked_app_validation(client, auth_headers, mock_pool):
    """ブロックアプリ追加バリデーション"""
    res = client.post(
        "/api/focus/app-guard/blocked-apps",
        headers=auth_headers,
        json={"package_name": "", "app_name": ""},
    )
    assert res.status_code == 422


def test_remove_blocked_app(client, auth_headers, mock_pool):
    """ブロックアプリ削除"""
    _, conn = mock_pool
    conn.execute.return_value = "DELETE 1"

    res = client.delete(
        "/api/focus/app-guard/blocked-apps/com.twitter.android",
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["deleted"] == "com.twitter.android"


def test_remove_blocked_app_not_found(client, auth_headers, mock_pool):
    """存在しないブロックアプリ削除"""
    _, conn = mock_pool
    conn.execute.return_value = "DELETE 0"

    res = client.delete(
        "/api/focus/app-guard/blocked-apps/com.nonexistent.app",
        headers=auth_headers,
    )
    assert res.status_code == 404


# === Summary ===


def test_get_summary(client, auth_headers, mock_pool):
    """ダッシュボードサマリー取得"""
    _, conn = mock_pool

    conn.fetchval.side_effect = [
        1500000,  # total_usage_ms
        3,  # blocked_count
    ]
    conn.fetch.return_value = [
        {
            "package_name": "com.twitter.android",
            "app_name": "Twitter",
            "total_ms": 900000,
        },
        {
            "package_name": "com.instagram.android",
            "app_name": "Instagram",
            "total_ms": 600000,
        },
    ]
    conn.fetchrow.side_effect = [
        {"count": 2, "total_ms": 8000},  # breach_stats
        {"native_block_mode": "soft"},  # mode_row
    ]

    res = client.get(
        "/api/focus/app-guard/summary?days=7",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_usage_ms"] == 1500000
    assert len(data["top_apps"]) == 2
    assert data["breach_count"] == 2
    assert data["total_breach_ms"] == 8000
    assert data["blocked_app_count"] == 3
    assert data["native_block_mode"] == "soft"


def test_get_summary_no_data(client, auth_headers, mock_pool):
    """サマリー取得（データなし）"""
    _, conn = mock_pool

    conn.fetchval.side_effect = [0, 0]
    conn.fetch.return_value = []
    conn.fetchrow.side_effect = [
        {"count": 0, "total_ms": 0},
        None,  # no lock settings
    ]

    res = client.get(
        "/api/focus/app-guard/summary?days=7",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_usage_ms"] == 0
    assert data["breach_count"] == 0
    assert data["native_block_mode"] == "off"
