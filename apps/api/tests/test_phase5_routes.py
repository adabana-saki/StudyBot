"""Phase 5 APIルートテスト - Activity, Buddy, Challenges, Sessions, Insights"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

GUILD_ID = 987654321
NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
TODAY = date(2025, 6, 15)


# ============================================================
# Activity
# ============================================================


class TestActivity:
    """アクティビティフィードエンドポイント"""

    def test_activity_feed(self, client, auth_headers, mock_pool):
        """ギルドのアクティビティフィード取得: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 111,
                "username": "Alice",
                "event_type": "study_start",
                "event_data": {"topic": "Python"},
                "created_at": NOW,
            },
            {
                "id": 2,
                "user_id": 222,
                "username": "Bob",
                "event_type": "achievement_unlock",
                "event_data": {"name": "初学者"},
                "created_at": NOW,
            },
        ]

        resp = client.get(f"/api/activity/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["user_id"] == 111
        assert data[0]["username"] == "Alice"
        assert data[0]["event_type"] == "study_start"
        assert data[0]["event_data"]["topic"] == "Python"
        assert data[1]["event_type"] == "achievement_unlock"

    def test_activity_feed_empty(self, client, auth_headers, mock_pool):
        """アクティビティフィード: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(f"/api/activity/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_activity_feed_json_string_event_data(self, client, auth_headers, mock_pool):
        """アクティビティフィード: event_dataがJSON文字列"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 111,
                "username": "Alice",
                "event_type": "study_start",
                "event_data": '{"topic": "Math"}',
                "created_at": NOW,
            },
        ]

        resp = client.get(f"/api/activity/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["event_data"]["topic"] == "Math"

    def test_activity_feed_unauthorized(self, client):
        """アクティビティフィード: 認証なし"""
        resp = client.get(f"/api/activity/{GUILD_ID}")
        assert resp.status_code == 403

    def test_studying_now(self, client, auth_headers, mock_pool):
        """現在勉強中のユーザー取得: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "user_id": 111,
                "username": "Alice",
                "event_type": "study_start",
                "event_data": {"topic": "Python"},
                "created_at": NOW,
            },
        ]

        resp = client.get(
            f"/api/activity/{GUILD_ID}/studying-now",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 111
        assert data[0]["username"] == "Alice"
        assert data[0]["event_type"] == "study_start"
        assert "started_at" in data[0]

    def test_studying_now_empty(self, client, auth_headers, mock_pool):
        """現在勉強中のユーザー: 誰もいない"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(
            f"/api/activity/{GUILD_ID}/studying-now",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_studying_now_unauthorized(self, client):
        """現在勉強中: 認証なし"""
        resp = client.get(f"/api/activity/{GUILD_ID}/studying-now")
        assert resp.status_code == 403


# ============================================================
# Buddy
# ============================================================


class TestBuddy:
    """バディエンドポイント"""

    def test_get_buddy_profile(self, client, auth_headers, mock_pool):
        """バディプロフィール取得: データあり"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "user_id": 123456789,
            "subjects": ["Python", "Math"],
            "preferred_times": ["morning", "evening"],
            "study_style": "focused",
            "active": True,
        }

        resp = client.get("/api/buddy/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == 123456789
        assert data["subjects"] == ["Python", "Math"]
        assert data["preferred_times"] == ["morning", "evening"]
        assert data["study_style"] == "focused"
        assert data["active"] is True

    def test_get_buddy_profile_not_found(self, client, auth_headers, mock_pool):
        """バディプロフィール取得: 未登録"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.get("/api/buddy/profile", headers=auth_headers)
        assert resp.status_code == 200
        # response_model allows None
        assert resp.json() is None

    def test_get_buddy_profile_unauthorized(self, client):
        """バディプロフィール: 認証なし"""
        resp = client.get("/api/buddy/profile")
        assert resp.status_code == 403

    def test_update_buddy_profile(self, client, auth_headers, mock_pool):
        """バディプロフィール更新: 正常"""
        _, conn = mock_pool
        conn.execute = AsyncMock()

        resp = client.put(
            "/api/buddy/profile",
            json={
                "subjects": ["Python", "JavaScript"],
                "preferred_times": ["morning"],
                "study_style": "collaborative",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == 123456789
        assert data["subjects"] == ["Python", "JavaScript"]
        assert data["preferred_times"] == ["morning"]
        assert data["study_style"] == "collaborative"
        assert data["active"] is True

    def test_update_buddy_profile_defaults(self, client, auth_headers, mock_pool):
        """バディプロフィール更新: デフォルト値"""
        _, conn = mock_pool
        conn.execute = AsyncMock()

        resp = client.put(
            "/api/buddy/profile",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["subjects"] == []
        assert data["preferred_times"] == []
        assert data["study_style"] == "focused"

    def test_update_buddy_profile_unauthorized(self, client):
        """バディプロフィール更新: 認証なし"""
        resp = client.put(
            "/api/buddy/profile",
            json={"subjects": ["Python"]},
        )
        assert resp.status_code == 403

    def test_get_buddy_matches(self, client, auth_headers, mock_pool):
        """バディマッチ取得: データあり"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_a": 123456789,
                "user_b": 222,
                "username_a": "TestUser",
                "username_b": "Alice",
                "guild_id": GUILD_ID,
                "subject": "Python",
                "compatibility_score": 0.85,
                "status": "active",
                "matched_at": NOW,
            },
            {
                "id": 2,
                "user_a": 333,
                "user_b": 123456789,
                "username_a": "Bob",
                "username_b": "TestUser",
                "guild_id": GUILD_ID,
                "subject": "Math",
                "compatibility_score": 0.72,
                "status": "active",
                "matched_at": NOW,
            },
        ]

        resp = client.get("/api/buddy/matches", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["user_a"] == 123456789
        assert data[0]["username_b"] == "Alice"
        assert data[0]["subject"] == "Python"
        assert data[0]["compatibility_score"] == 0.85
        assert data[1]["username_a"] == "Bob"

    def test_get_buddy_matches_empty(self, client, auth_headers, mock_pool):
        """バディマッチ取得: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get("/api/buddy/matches", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_buddy_matches_unauthorized(self, client):
        """バディマッチ: 認証なし"""
        resp = client.get("/api/buddy/matches")
        assert resp.status_code == 403


# ============================================================
# Challenges
# ============================================================


class TestChallenges:
    """チャレンジエンドポイント"""

    def _challenge_row(self, **overrides):
        """テスト用チャレンジ行"""
        base = {
            "id": 1,
            "creator_id": 111,
            "creator_name": "Alice",
            "guild_id": GUILD_ID,
            "name": "1週間100時間チャレンジ",
            "description": "みんなで頑張ろう",
            "goal_type": "study_minutes",
            "goal_target": 6000,
            "duration_days": 7,
            "start_date": TODAY,
            "end_date": date(2025, 6, 22),
            "xp_multiplier": 1.5,
            "status": "active",
            "participant_count": 5,
            "created_at": NOW,
        }
        base.update(overrides)
        return base

    def test_list_challenges(self, client, auth_headers, mock_pool):
        """チャレンジ一覧: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            self._challenge_row(),
            self._challenge_row(
                id=2,
                name="30日連続学習",
                goal_type="streak_days",
                goal_target=30,
                duration_days=30,
                participant_count=12,
            ),
        ]

        resp = client.get("/api/challenges", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "1週間100時間チャレンジ"
        assert data[0]["goal_type"] == "study_minutes"
        assert data[0]["participant_count"] == 5
        assert data[1]["name"] == "30日連続学習"
        assert data[1]["participant_count"] == 12

    def test_list_challenges_empty(self, client, auth_headers, mock_pool):
        """チャレンジ一覧: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get("/api/challenges", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_challenges_unauthorized(self, client):
        """チャレンジ一覧: 認証なし"""
        resp = client.get("/api/challenges")
        assert resp.status_code == 403

    def test_challenge_detail(self, client, auth_headers, mock_pool):
        """チャレンジ詳細: 正常"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._challenge_row()
        conn.fetch.return_value = [
            {
                "user_id": 111,
                "username": "Alice",
                "progress": 3000,
                "checkins": 5,
                "completed": False,
            },
            {
                "user_id": 222,
                "username": "Bob",
                "progress": 6000,
                "checkins": 7,
                "completed": True,
            },
        ]

        resp = client.get("/api/challenges/1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "1週間100時間チャレンジ"
        assert len(data["participants"]) == 2
        assert data["participants"][0]["username"] == "Alice"
        assert data["participants"][0]["progress"] == 3000
        assert data["participants"][1]["completed"] is True

    def test_challenge_detail_not_found(self, client, auth_headers, mock_pool):
        """チャレンジ詳細: 存在しない"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.get("/api/challenges/999", headers=auth_headers)
        assert resp.status_code == 404

    def test_join_challenge(self, client, auth_headers, mock_pool):
        """チャレンジ参加: 正常"""
        _, conn = mock_pool
        # First fetchrow: find active challenge
        # Second fetchrow: check existing participant (None = not joined)
        conn.fetchrow.side_effect = [
            self._challenge_row(status="active"),
            None,
        ]
        conn.execute = AsyncMock()

        resp = client.post("/api/challenges/1/join", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "チャレンジに参加しました"

    def test_join_challenge_not_found(self, client, auth_headers, mock_pool):
        """チャレンジ参加: アクティブなチャレンジがない"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.post("/api/challenges/999/join", headers=auth_headers)
        assert resp.status_code == 404

    def test_join_challenge_already_joined(self, client, auth_headers, mock_pool):
        """チャレンジ参加: 既に参加済み"""
        _, conn = mock_pool
        conn.fetchrow.side_effect = [
            self._challenge_row(status="active"),
            {"id": 1},  # existing participant
        ]

        resp = client.post("/api/challenges/1/join", headers=auth_headers)
        assert resp.status_code == 400
        assert "既に参加" in resp.json()["detail"]

    def test_join_challenge_unauthorized(self, client):
        """チャレンジ参加: 認証なし"""
        resp = client.post("/api/challenges/1/join")
        assert resp.status_code == 403


# ============================================================
# Sessions
# ============================================================


class TestSessions:
    """セッションエンドポイント"""

    def test_get_active_sessions(self, client, auth_headers, mock_pool):
        """アクティブセッション取得: 正常"""
        _, conn = mock_pool
        end_time = NOW + timedelta(minutes=25)
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 111,
                "username": "Alice",
                "session_type": "pomodoro",
                "source_platform": "web",
                "topic": "Python",
                "duration_minutes": 25,
                "started_at": NOW,
                "end_time": end_time,
            },
            {
                "id": 2,
                "user_id": 222,
                "username": "Bob",
                "session_type": "focus",
                "source_platform": "discord",
                "topic": "",
                "duration_minutes": 60,
                "started_at": NOW,
                "end_time": NOW + timedelta(minutes=60),
            },
        ]

        resp = client.get("/api/sessions/active", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["user_id"] == 111
        assert data[0]["session_type"] == "pomodoro"
        assert data[0]["source_platform"] == "web"
        assert data[0]["topic"] == "Python"
        assert data[0]["duration_minutes"] == 25
        assert "remaining_seconds" in data[0]
        assert data[1]["session_type"] == "focus"

    def test_get_active_sessions_empty(self, client, auth_headers, mock_pool):
        """アクティブセッション: なし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get("/api/sessions/active", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_active_sessions_unauthorized(self, client):
        """アクティブセッション: 認証なし"""
        resp = client.get("/api/sessions/active")
        assert resp.status_code == 403

    @patch(
        "api.services.redis_client.get_redis",
        side_effect=Exception("Redis unavailable"),
    )
    def test_start_session(self, _mock_redis, client, auth_headers, mock_pool):
        """セッション開始: 正常 (Redis失敗でも成功)"""
        _, conn = mock_pool
        conn.execute = AsyncMock()
        conn.fetchval.return_value = 42

        resp = client.post(
            "/api/sessions/start",
            json={
                "session_type": "pomodoro",
                "duration_minutes": 25,
                "topic": "Python学習",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 42
        assert data["user_id"] == 123456789
        assert data["username"] == "TestUser"
        assert data["session_type"] == "pomodoro"
        assert data["source_platform"] == "web"
        assert data["topic"] == "Python学習"
        assert data["duration_minutes"] == 25
        assert data["remaining_seconds"] == 25 * 60

    @patch(
        "api.services.redis_client.get_redis",
        side_effect=Exception("Redis unavailable"),
    )
    def test_start_session_no_topic(self, _mock_redis, client, auth_headers, mock_pool):
        """セッション開始: トピックなし"""
        _, conn = mock_pool
        conn.execute = AsyncMock()
        conn.fetchval.return_value = 43

        resp = client.post(
            "/api/sessions/start",
            json={
                "session_type": "focus",
                "duration_minutes": 60,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic"] == ""
        assert data["duration_minutes"] == 60

    def test_start_session_unauthorized(self, client):
        """セッション開始: 認証なし"""
        resp = client.post(
            "/api/sessions/start",
            json={
                "session_type": "pomodoro",
                "duration_minutes": 25,
            },
        )
        assert resp.status_code == 403


# ============================================================
# Insights
# ============================================================


class TestInsights:
    """インサイトエンドポイント"""

    def test_get_my_insights(self, client, auth_headers, mock_pool):
        """インサイト取得: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "insight_type": "productivity",
                "title": "朝の学習が効果的",
                "body": "あなたは朝の時間帯に最も集中力が高いようです。",
                "data": {"peak_hour": 9, "avg_focus": 85},
                "confidence": 0.82,
                "generated_at": NOW,
            },
            {
                "id": 2,
                "insight_type": "streak",
                "title": "連続学習記録",
                "body": "12日連続で学習しています。素晴らしい!",
                "data": {},
                "confidence": 0.95,
                "generated_at": NOW,
            },
        ]

        resp = client.get("/api/insights/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["insight_type"] == "productivity"
        assert data[0]["title"] == "朝の学習が効果的"
        assert data[0]["data"]["peak_hour"] == 9
        assert data[0]["confidence"] == 0.82
        assert data[1]["insight_type"] == "streak"

    def test_get_my_insights_json_string_data(self, client, auth_headers, mock_pool):
        """インサイト取得: dataがJSON文字列"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "insight_type": "tip",
                "title": "ポモドーロ推奨",
                "body": "25分集中+5分休憩が効果的です。",
                "data": '{"method": "pomodoro"}',
                "confidence": 0.7,
                "generated_at": NOW,
            },
        ]

        resp = client.get("/api/insights/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["data"]["method"] == "pomodoro"

    def test_get_my_insights_empty(self, client, auth_headers, mock_pool):
        """インサイト取得: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get("/api/insights/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_my_insights_unauthorized(self, client):
        """インサイト: 認証なし"""
        resp = client.get("/api/insights/me")
        assert resp.status_code == 403

    def test_get_my_reports(self, client, auth_headers, mock_pool):
        """週次レポート一覧: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 123456789,
                "week_start": date(2025, 6, 9),
                "week_end": date(2025, 6, 15),
                "summary": "今週は420分学習しました。先週比+15%。",
                "insights": [
                    {"type": "productivity", "text": "朝に集中力が高い"},
                ],
                "generated_at": NOW,
                "sent_via_dm": True,
            },
            {
                "id": 2,
                "user_id": 123456789,
                "week_start": date(2025, 6, 2),
                "week_end": date(2025, 6, 8),
                "summary": "今週は365分学習しました。",
                "insights": [],
                "generated_at": NOW,
                "sent_via_dm": False,
            },
        ]

        resp = client.get("/api/insights/me/reports", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["week_start"] == "2025-06-09"
        assert data[0]["week_end"] == "2025-06-15"
        assert "420分" in data[0]["summary"]
        assert len(data[0]["insights"]) == 1
        assert data[1]["insights"] == []

    def test_get_my_reports_json_string_insights(self, client, auth_headers, mock_pool):
        """週次レポート: insightsがJSON文字列"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 123456789,
                "week_start": date(2025, 6, 9),
                "week_end": date(2025, 6, 15),
                "summary": "良い週でした。",
                "insights": '[{"type": "tip", "text": "継続は力"}]',
                "generated_at": NOW,
                "sent_via_dm": True,
            },
        ]

        resp = client.get("/api/insights/me/reports", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["insights"][0]["type"] == "tip"

    def test_get_my_reports_empty(self, client, auth_headers, mock_pool):
        """週次レポート一覧: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get("/api/insights/me/reports", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_my_reports_unauthorized(self, client):
        """週次レポート: 認証なし"""
        resp = client.get("/api/insights/me/reports")
        assert resp.status_code == 403
