"""システムステータスAPIのテスト"""

import json
from unittest.mock import AsyncMock, MagicMock, patch


# === GET /api/status ===


def test_status_all_healthy(client, mock_pool):
    """全コンポーネント正常"""
    _, conn = mock_pool
    conn.fetchval.return_value = 1

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = json.dumps(
        {
            "bot_name": "StudyBot#1234",
            "guild_count": 5,
            "ws_latency_ms": 42.3,
            "updated_at": "2026-03-01T00:00:00+00:00",
        }
    )

    mock_push_svc = MagicMock()
    mock_push_svc._initialized = True

    with (
        patch("api.routes.status.get_pool") as mock_get_pool,
        patch("api.services.redis_client.get_redis", return_value=mock_redis),
        patch("api.services.push_service.get_push_service", return_value=mock_push_svc),
    ):
        mock_get_pool.return_value = mock_pool[0]
        res = client.get("/api/status")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"
    assert len(data["components"]) == 4
    assert all(c["status"] == "ok" for c in data["components"])

    # Discord Bot details
    bot_comp = next(c for c in data["components"] if c["name"] == "Discord Bot")
    assert bot_comp["details"]["bot_name"] == "StudyBot#1234"
    assert bot_comp["details"]["guild_count"] == 5
    assert bot_comp["latency_ms"] == 42.3


def test_status_bot_offline(client, mock_pool):
    """Botオフライン時 → status=degraded"""
    _, conn = mock_pool
    conn.fetchval.return_value = 1

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None  # ハートビートなし

    mock_push_svc = MagicMock()
    mock_push_svc._initialized = True

    with (
        patch("api.routes.status.get_pool") as mock_get_pool,
        patch("api.services.redis_client.get_redis", return_value=mock_redis),
        patch("api.services.push_service.get_push_service", return_value=mock_push_svc),
    ):
        mock_get_pool.return_value = mock_pool[0]
        res = client.get("/api/status")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "degraded"

    bot_comp = next(c for c in data["components"] if c["name"] == "Discord Bot")
    assert bot_comp["status"] == "down"


def test_status_no_auth_required(client, mock_pool):
    """認証なしでアクセス可能"""
    _, conn = mock_pool
    conn.fetchval.return_value = 1

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None

    mock_push_svc = MagicMock()
    mock_push_svc._initialized = False

    with (
        patch("api.routes.status.get_pool") as mock_get_pool,
        patch("api.services.redis_client.get_redis", return_value=mock_redis),
        patch("api.services.push_service.get_push_service", return_value=mock_push_svc),
    ):
        mock_get_pool.return_value = mock_pool[0]
        # auth_headersなし
        res = client.get("/api/status")

    assert res.status_code == 200


def test_status_firebase_degraded(client, mock_pool):
    """Firebase未初期化 → degradedではなくfirebaseのみdegraded"""
    _, conn = mock_pool
    conn.fetchval.return_value = 1

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = json.dumps(
        {"bot_name": "Bot", "guild_count": 1, "ws_latency_ms": 50, "updated_at": ""}
    )

    mock_push_svc = MagicMock()
    mock_push_svc._initialized = False

    with (
        patch("api.routes.status.get_pool") as mock_get_pool,
        patch("api.services.redis_client.get_redis", return_value=mock_redis),
        patch("api.services.push_service.get_push_service", return_value=mock_push_svc),
    ):
        mock_get_pool.return_value = mock_pool[0]
        res = client.get("/api/status")

    data = res.json()
    fb = next(c for c in data["components"] if c["name"] == "Firebase")
    assert fb["status"] == "degraded"
    # degradedはdownではないのでoverall statusは "ok" のまま
    # (has_down checks for "down", not "degraded")
    assert data["status"] == "ok"


# === POST /api/status/ping ===


def test_ping_success(client, auth_headers, mock_pool):
    """テスト通知送信成功"""
    mock_push_svc = MagicMock()
    mock_push_svc._initialized = True
    mock_push_svc.send_to_user = AsyncMock(return_value=2)

    with patch("api.services.push_service.get_push_service", return_value=mock_push_svc):
        res = client.post("/api/status/ping", headers=auth_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["sent"] == 2
    assert "2件" in data["message"]


def test_ping_no_devices(client, auth_headers, mock_pool):
    """登録デバイスなし"""
    mock_push_svc = MagicMock()
    mock_push_svc._initialized = True
    mock_push_svc.send_to_user = AsyncMock(return_value=0)

    with patch("api.services.push_service.get_push_service", return_value=mock_push_svc):
        res = client.post("/api/status/ping", headers=auth_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["sent"] == 0
    assert "登録デバイスがありません" in data["message"]


def test_ping_requires_auth(client, mock_pool):
    """認証なしでping → 403"""
    res = client.post("/api/status/ping")
    assert res.status_code == 403


def test_ping_service_not_initialized(client, auth_headers, mock_pool):
    """プッシュサービス未初期化"""
    with patch(
        "api.services.push_service.get_push_service",
        side_effect=RuntimeError("PushNotificationService未初期化"),
    ):
        res = client.post("/api/status/ping", headers=auth_headers)

    assert res.status_code == 503


def test_ping_firebase_not_initialized(client, auth_headers, mock_pool):
    """Firebase未初期化"""
    mock_push_svc = MagicMock()
    mock_push_svc._initialized = False

    with patch("api.services.push_service.get_push_service", return_value=mock_push_svc):
        res = client.post("/api/status/ping", headers=auth_headers)

    assert res.status_code == 503
