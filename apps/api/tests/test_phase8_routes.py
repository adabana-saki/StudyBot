"""Phase 8 APIルートテスト - Timeline, Battles, ServerAnalytics, Rooms"""

import json
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

GUILD_ID = 987654321
NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
TODAY = date(2025, 6, 15)


# ============================================================
# Social Timeline
# ============================================================


class TestTimeline:
    """ソーシャルタイムラインエンドポイント"""

    def test_get_timeline(self, client, auth_headers, mock_pool):
        """タイムライン取得: リアクション数・コメント数付き"""
        _, conn = mock_pool
        events_rows = [
            {
                "id": 1,
                "user_id": 111,
                "username": "Alice",
                "event_type": "study_start",
                "event_data": {"topic": "Python"},
                "created_at": NOW,
                "reaction_counts": {"applaud": 2},
                "comment_count": 3,
            },
            {
                "id": 2,
                "user_id": 222,
                "username": "Bob",
                "event_type": "achievement_unlock",
                "event_data": {"name": "初学者"},
                "created_at": NOW,
                "reaction_counts": {},
                "comment_count": 0,
            },
        ]
        my_reactions_rows = [
            {"event_id": 1, "reaction_type": "applaud"},
        ]
        conn.fetchval.return_value = 2
        conn.fetch.side_effect = [events_rows, my_reactions_rows]

        resp = client.get(f"/api/timeline/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["user_id"] == 111
        assert data["items"][0]["reaction_counts"] == {"applaud": 2}
        assert data["items"][0]["comment_count"] == 3
        assert data["items"][0]["my_reactions"] == ["applaud"]
        assert data["items"][1]["my_reactions"] == []

    def test_get_timeline_empty(self, client, auth_headers, mock_pool):
        """タイムライン取得: データなし"""
        _, conn = mock_pool
        conn.fetchval.return_value = 0
        conn.fetch.side_effect = [[], []]

        resp = client.get(f"/api/timeline/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    @patch("api.services.redis_client.get_redis", return_value=None)
    def test_add_reaction(self, _mock_redis, client, auth_headers, mock_pool):
        """リアクション追加: 正常"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {"id": 1, "user_id": 222}
        conn.execute.return_value = None

        resp = client.post(
            "/api/timeline/1/reactions",
            json={"reaction_type": "fire"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_add_reaction_invalid_type(self, client, auth_headers, mock_pool):
        """リアクション追加: 無効なタイプ"""
        _, conn = mock_pool

        resp = client.post(
            "/api/timeline/1/reactions",
            json={"reaction_type": "invalid_type"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_add_reaction_event_not_found(self, client, auth_headers, mock_pool):
        """リアクション追加: イベントが見つからない"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.post(
            "/api/timeline/9999/reactions",
            json={"reaction_type": "applaud"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_comments(self, client, auth_headers, mock_pool):
        """コメント一覧取得"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "user_id": 111,
                "username": "Alice",
                "body": "すごい！",
                "created_at": NOW,
            },
            {
                "id": 2,
                "user_id": 222,
                "username": "Bob",
                "body": "頑張って！",
                "created_at": NOW,
            },
        ]

        resp = client.get("/api/timeline/1/comments", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["body"] == "すごい！"
        assert data[1]["username"] == "Bob"

    @patch("api.services.redis_client.get_redis", return_value=None)
    def test_add_comment(self, _mock_redis, client, auth_headers, mock_pool):
        """コメント投稿: 正常"""
        _, conn = mock_pool
        event_row = {"id": 1, "user_id": 222}
        insert_row = {"id": 10, "created_at": NOW}
        conn.fetchrow.side_effect = [event_row, insert_row]

        resp = client.post(
            "/api/timeline/1/comments",
            json={"body": "頑張って！"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 10
        assert data["body"] == "頑張って！"

    def test_add_comment_event_not_found(self, client, auth_headers, mock_pool):
        """コメント投稿: イベントが見つからない"""
        _, conn = mock_pool
        conn.fetchrow.side_effect = [None]

        resp = client.post(
            "/api/timeline/9999/comments",
            json={"body": "テスト"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_delete_own_comment(self, client, auth_headers, mock_pool):
        """自分のコメント削除: 正常"""
        _, conn = mock_pool
        # current_user has user_id 123456789
        conn.fetchrow.return_value = {"user_id": 123456789}
        conn.execute.return_value = None

        resp = client.delete("/api/timeline/comments/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_delete_other_comment_forbidden(self, client, auth_headers, mock_pool):
        """他人のコメント削除: 403"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {"user_id": 999999}

        resp = client.delete("/api/timeline/comments/1", headers=auth_headers)
        assert resp.status_code == 403

    def test_delete_comment_not_found(self, client, auth_headers, mock_pool):
        """コメント削除: コメントが見つからない"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.delete("/api/timeline/comments/999", headers=auth_headers)
        assert resp.status_code == 404


# ============================================================
# Battles
# ============================================================


class TestBattles:
    """チームバトルエンドポイント"""

    def _make_battle_row(self, **overrides):
        """バトル行データ生成ヘルパー"""
        row = {
            "id": 1,
            "guild_id": GUILD_ID,
            "goal_type": "study_minutes",
            "duration_days": 7,
            "start_date": TODAY,
            "end_date": date(2025, 6, 22),
            "status": "active",
            "xp_multiplier": 1.5,
            "team_a_id": 10,
            "team_b_id": 20,
            "team_a_score": 500,
            "team_b_score": 300,
            "winner_team_id": None,
            "team_a_name": "Alpha",
            "team_b_name": "Beta",
            "team_a_members": 5,
            "team_b_members": 4,
            "created_at": NOW,
        }
        row.update(overrides)
        return row

    def test_get_battles(self, client, auth_headers, mock_pool):
        """バトル一覧取得: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            self._make_battle_row(),
            self._make_battle_row(id=2, status="pending", team_a_score=0, team_b_score=0),
        ]

        resp = client.get(f"/api/battles/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["goal_type"] == "study_minutes"
        assert data[0]["team_a"]["name"] == "Alpha"
        assert data[0]["team_a"]["score"] == 500
        assert data[0]["team_a"]["member_count"] == 5
        assert data[0]["team_b"]["name"] == "Beta"
        assert data[0]["winner_team_id"] is None
        assert data[1]["status"] == "pending"

    def test_get_battles_empty(self, client, auth_headers, mock_pool):
        """バトル一覧: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(f"/api/battles/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_battle_detail(self, client, auth_headers, mock_pool):
        """バトル詳細取得: 正常"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._make_battle_row()
        conn.fetch.return_value = [
            {
                "user_id": 111,
                "username": "Alice",
                "team_id": 10,
                "total_contribution": 120,
                "source": "study_minutes",
            },
            {
                "user_id": 222,
                "username": "Bob",
                "team_id": 20,
                "total_contribution": 80,
                "source": "study_minutes",
            },
        ]

        resp = client.get(f"/api/battles/{GUILD_ID}/1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["team_a"]["name"] == "Alpha"
        assert len(data["contributions"]) == 2
        assert data["contributions"][0]["username"] == "Alice"
        assert data["contributions"][0]["contribution"] == 120

    def test_get_battle_not_found(self, client, auth_headers, mock_pool):
        """バトル詳細: 404"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.get(f"/api/battles/{GUILD_ID}/9999", headers=auth_headers)
        assert resp.status_code == 404


# ============================================================
# Server Analytics
# ============================================================


class TestServerAnalytics:
    """サーバーコマンドセンターエンドポイント"""

    def test_engagement(self, client, auth_headers, mock_pool):
        """エンゲージメント推移: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "date": TODAY,
                "active_users": 15,
                "sessions": 30,
                "total_minutes": 450,
            },
            {
                "date": date(2025, 6, 14),
                "active_users": 12,
                "sessions": 25,
                "total_minutes": 380,
            },
        ]

        resp = client.get(
            f"/api/server/{GUILD_ID}/analytics/engagement",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["active_users"] == 15
        assert data[0]["sessions"] == 30
        assert data[0]["total_minutes"] == 450

    def test_engagement_empty(self, client, auth_headers, mock_pool):
        """エンゲージメント推移: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(
            f"/api/server/{GUILD_ID}/analytics/engagement",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_at_risk(self, client, auth_headers, mock_pool):
        """離脱リスクメンバー: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "user_id": 111,
                "username": "Alice",
                "best_streak": 10,
                "last_study_date": TODAY,
                "days_inactive": 8,
                "risk_score": 0.7,
            },
        ]

        resp = client.get(
            f"/api/server/{GUILD_ID}/analytics/at-risk",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 111
        assert data[0]["best_streak"] == 10
        assert data[0]["risk_score"] == 0.7

    def test_topics(self, client, auth_headers, mock_pool):
        """トピック分析: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "topic": "Python",
                "count": 50,
                "total_minutes": 1500,
                "this_week": 20,
                "last_week": 15,
            },
            {
                "topic": "数学",
                "count": 30,
                "total_minutes": 900,
                "this_week": 10,
                "last_week": 12,
            },
        ]

        resp = client.get(
            f"/api/server/{GUILD_ID}/analytics/topics",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["topic"] == "Python"
        assert data[0]["count"] == 50

    def test_optimal_times(self, client, auth_headers, mock_pool):
        """最適イベント時間: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "day_of_week": 1,
                "hour": 20,
                "session_count": 15,
                "total_minutes": 450,
            },
        ]

        resp = client.get(
            f"/api/server/{GUILD_ID}/analytics/optimal-times",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["day_of_week"] == 1
        assert data[0]["hour"] == 20

    def test_community_health(self, client, auth_headers, mock_pool):
        """コミュニティ健全性スコア: 正常"""
        _, conn = mock_pool
        # fetchval is called 6 times:
        #   dau=5, mau=20, avg_streak=4.5,
        #   active_this_week=15, active_last_week=18, churned=3
        conn.fetchval.side_effect = [5, 20, 4.5, 15, 18, 3]

        resp = client.get(
            f"/api/server/{GUILD_ID}/analytics/health",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "dau_mau_ratio" in data
        assert "retention_rate" in data
        assert "avg_streak" in data
        assert "churn_rate" in data
        # Verify computed values
        assert data["dau_mau_ratio"] == round(5 / 20, 3)
        assert data["retention_rate"] == round(15 / 18, 3)
        assert data["avg_streak"] == 4.5
        assert data["churn_rate"] == round(3 / 18, 3)
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100

    def test_community_health_zero_mau(self, client, auth_headers, mock_pool):
        """コミュニティ健全性: MAU=0でもゼロ除算しない"""
        _, conn = mock_pool
        # dau=0, mau=0 (becomes 1), avg_streak=0,
        # active_this_week=0, active_last_week=0 (becomes 1), churned=0
        conn.fetchval.side_effect = [0, 0, 0, 0, 0, 0]

        resp = client.get(
            f"/api/server/{GUILD_ID}/analytics/health",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["score"], int)

    @patch("api.services.redis_client.get_redis")
    def test_create_action_immediate(self, mock_get_redis, client, auth_headers, mock_pool):
        """アクション作成: 即時実行（Redis publish）"""
        _, conn = mock_pool
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        resp = client.post(
            f"/api/server/{GUILD_ID}/actions",
            json={
                "action_type": "send_dm",
                "action_data": {"user_id": 111, "message": "テスト"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "dispatched"

    def test_create_action_scheduled(self, client, auth_headers, mock_pool):
        """アクション作成: スケジュール実行"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": 1,
            "scheduled_for": NOW,
        }

        resp = client.post(
            f"/api/server/{GUILD_ID}/actions",
            json={
                "action_type": "announce",
                "action_data": {"message": "お知らせ"},
                "scheduled_for": NOW.isoformat(),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "scheduled"
        assert data["id"] == 1

    def test_create_action_invalid_type(self, client, auth_headers, mock_pool):
        """アクション作成: 無効なタイプ"""
        _, conn = mock_pool

        resp = client.post(
            f"/api/server/{GUILD_ID}/actions",
            json={
                "action_type": "invalid_action",
                "action_data": {},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_get_actions(self, client, auth_headers, mock_pool):
        """アクション履歴取得: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": 1,
                "action_type": "send_dm",
                "action_data": json.dumps({"user_id": 111}),
                "scheduled_for": NOW,
                "executed": True,
                "result": "success",
                "created_by": 123456789,
                "created_at": NOW,
            },
            {
                "id": 2,
                "action_type": "announce",
                "action_data": {"message": "テスト"},
                "scheduled_for": None,
                "executed": False,
                "result": None,
                "created_by": 123456789,
                "created_at": NOW,
            },
        ]

        resp = client.get(
            f"/api/server/{GUILD_ID}/actions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["action_type"] == "send_dm"
        assert data[0]["action_data"] == {"user_id": 111}
        assert data[0]["executed"] is True
        assert data[1]["scheduled_for"] is None
        assert data[1]["executed"] is False


# ============================================================
# Rooms
# ============================================================


class TestRooms:
    """スタディルームエンドポイント"""

    def _make_room_row(self, **overrides):
        """ルーム行データ生成ヘルパー"""
        row = {
            "id": 1,
            "guild_id": GUILD_ID,
            "name": "Python勉強部屋",
            "description": "Python学習用ルーム",
            "theme": "programming",
            "collective_goal_minutes": 1000,
            "collective_progress_minutes": 450,
            "max_occupants": 10,
            "member_count": 3,
            "state": "active",
            "created_at": NOW,
        }
        row.update(overrides)
        return row

    def test_get_campus(self, client, auth_headers, mock_pool):
        """キャンパス（全ルーム一覧）取得: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            self._make_room_row(),
            self._make_room_row(id=2, name="数学ルーム", member_count=5),
        ]

        resp = client.get(f"/api/rooms/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Python勉強部屋"
        assert data[0]["member_count"] == 3
        assert data[0]["max_occupants"] == 10
        assert data[0]["collective_goal_minutes"] == 1000
        assert data[1]["name"] == "数学ルーム"

    def test_get_campus_empty(self, client, auth_headers, mock_pool):
        """キャンパス: ルームなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(f"/api/rooms/{GUILD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_room_detail(self, client, auth_headers, mock_pool):
        """ルーム詳細取得: メンバーリスト付き"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._make_room_row()
        conn.fetch.return_value = [
            {
                "user_id": 111,
                "username": "Alice",
                "platform": "discord",
                "topic": "Python基礎",
                "joined_at": NOW,
            },
            {
                "user_id": 222,
                "username": "Bob",
                "platform": "web",
                "topic": "Django",
                "joined_at": NOW,
            },
        ]

        resp = client.get(f"/api/rooms/{GUILD_ID}/1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "Python勉強部屋"
        assert data["member_count"] == 3
        assert len(data["members"]) == 2
        assert data["members"][0]["username"] == "Alice"
        assert data["members"][0]["platform"] == "discord"
        assert data["members"][1]["topic"] == "Django"

    def test_room_not_found(self, client, auth_headers, mock_pool):
        """ルーム詳細: 404"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.get(f"/api/rooms/{GUILD_ID}/9999", headers=auth_headers)
        assert resp.status_code == 404

    @patch("api.services.redis_client.get_redis", return_value=None)
    def test_join_room(self, _mock_redis, client, auth_headers, mock_pool):
        """ルーム参加: 正常"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._make_room_row(max_occupants=10)
        conn.fetchval.return_value = 3  # current member count < max_occupants
        conn.execute.return_value = None

        resp = client.post(
            f"/api/rooms/{GUILD_ID}/1/join",
            json={"topic": "FastAPI"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "joined"
        assert data["room_id"] == 1

    @patch("api.services.redis_client.get_redis", return_value=None)
    def test_join_room_full(self, _mock_redis, client, auth_headers, mock_pool):
        """ルーム参加: 満員で409"""
        _, conn = mock_pool
        conn.fetchrow.return_value = self._make_room_row(max_occupants=5)
        conn.fetchval.return_value = 5  # member_count == max_occupants
        conn.execute.return_value = None

        resp = client.post(
            f"/api/rooms/{GUILD_ID}/1/join",
            json={"topic": "テスト"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_join_room_not_found(self, client, auth_headers, mock_pool):
        """ルーム参加: ルームが見つからない"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.post(
            f"/api/rooms/{GUILD_ID}/9999/join",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @patch("api.services.redis_client.get_redis", return_value=None)
    def test_leave_room(self, _mock_redis, client, auth_headers, mock_pool):
        """ルーム退出: 正常"""
        _, conn = mock_pool
        conn.fetchrow.return_value = {
            "user_id": 123456789,
            "room_id": 1,
            "platform": "web",
            "topic": "Python",
            "joined_at": datetime(2025, 6, 15, 11, 0, 0, tzinfo=UTC),
        }
        conn.execute.return_value = None

        resp = client.post(
            f"/api/rooms/{GUILD_ID}/1/leave",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "left"
        assert "duration_minutes" in data

    def test_leave_room_not_member(self, client, auth_headers, mock_pool):
        """ルーム退出: 参加していない"""
        _, conn = mock_pool
        conn.fetchrow.return_value = None

        resp = client.post(
            f"/api/rooms/{GUILD_ID}/1/leave",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_history(self, client, auth_headers, mock_pool):
        """ルーム利用履歴: 正常"""
        _, conn = mock_pool
        conn.fetch.return_value = [
            {
                "user_id": 111,
                "username": "Alice",
                "platform": "discord",
                "joined_at": NOW,
                "left_at": datetime(2025, 6, 15, 13, 0, 0, tzinfo=UTC),
                "duration_minutes": 60,
            },
            {
                "user_id": 222,
                "username": "Bob",
                "platform": "web",
                "joined_at": NOW,
                "left_at": None,
                "duration_minutes": 30,
            },
        ]

        resp = client.get(
            f"/api/rooms/{GUILD_ID}/1/history",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["username"] == "Alice"
        assert data[0]["duration_minutes"] == 60
        assert data[0]["left_at"] is not None
        assert data[1]["left_at"] is None

    def test_get_history_empty(self, client, auth_headers, mock_pool):
        """ルーム利用履歴: データなし"""
        _, conn = mock_pool
        conn.fetch.return_value = []

        resp = client.get(
            f"/api/rooms/{GUILD_ID}/1/history",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []
