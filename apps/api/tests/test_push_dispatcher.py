"""PushDispatcher テスト"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.push_dispatcher import TEMPLATES, PushDispatcher


@pytest.fixture
def mock_push_service():
    """モックPushNotificationService"""
    svc = AsyncMock()
    svc.send_to_user = AsyncMock(return_value=1)
    return svc


@pytest.fixture
def mock_redis():
    """モックRedis接続"""
    r = MagicMock()
    r.pubsub = MagicMock()
    return r


class TestPushDispatcherHandleEvent:
    """イベント処理テスト"""

    @pytest.mark.asyncio
    async def test_level_up_event(self, mock_redis, mock_push_service):
        """level_upイベントでプッシュ通知送信"""
        dispatcher = PushDispatcher(mock_redis, mock_push_service)

        event = json.dumps({
            "type": "level_up",
            "data": {"user_id": 123, "new_level": 5, "guild_id": 999},
        })

        await dispatcher._handle_event(event)

        mock_push_service.send_to_user.assert_called_once_with(
            user_id=123,
            title="レベルアップ!",
            body="レベル5になりました!",
            data={"event_type": "level_up", "user_id": 123, "new_level": 5, "guild_id": 999},
            notification_type="level_up",
        )

    @pytest.mark.asyncio
    async def test_achievement_unlock_event(self, mock_redis, mock_push_service):
        """achievement_unlockイベント"""
        dispatcher = PushDispatcher(mock_redis, mock_push_service)

        event = json.dumps({
            "type": "achievement_unlock",
            "data": {
                "user_id": 456,
                "achievement_emoji": "🏆",
                "achievement_name": "100時間学習",
                "guild_id": 999,
            },
        })

        await dispatcher._handle_event(event)

        mock_push_service.send_to_user.assert_called_once()
        call_kwargs = mock_push_service.send_to_user.call_args[1]
        assert call_kwargs["title"] == "🏆 実績解除!"
        assert call_kwargs["body"] == "100時間学習を獲得!"

    @pytest.mark.asyncio
    async def test_pomodoro_complete_event(self, mock_redis, mock_push_service):
        """pomodoro_completeイベント"""
        dispatcher = PushDispatcher(mock_redis, mock_push_service)

        event = json.dumps({
            "type": "pomodoro_complete",
            "data": {
                "user_id": 789,
                "topic": "数学",
                "work_minutes": 25,
                "guild_id": 999,
            },
        })

        await dispatcher._handle_event(event)

        call_kwargs = mock_push_service.send_to_user.call_args[1]
        assert call_kwargs["title"] == "ポモドーロ完了!"
        assert call_kwargs["body"] == "数学 - 25分集中しました"

    @pytest.mark.asyncio
    async def test_app_breach_event(self, mock_redis, mock_push_service):
        """app_breachイベント"""
        dispatcher = PushDispatcher(mock_redis, mock_push_service)

        event = json.dumps({
            "type": "app_breach",
            "data": {"user_id": 101, "guild_id": 999},
        })

        await dispatcher._handle_event(event)

        call_kwargs = mock_push_service.send_to_user.call_args[1]
        assert call_kwargs["title"] == "集中モード警告"
        assert call_kwargs["body"] == "ブロック対象アプリが使用されました"

    @pytest.mark.asyncio
    async def test_unknown_event_skipped(self, mock_redis, mock_push_service):
        """未対応イベント種別はスキップ"""
        dispatcher = PushDispatcher(mock_redis, mock_push_service)

        event = json.dumps({
            "type": "unknown_event",
            "data": {"user_id": 123},
        })

        await dispatcher._handle_event(event)
        mock_push_service.send_to_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_without_user_id_skipped(self, mock_redis, mock_push_service):
        """user_idなしイベントはスキップ"""
        dispatcher = PushDispatcher(mock_redis, mock_push_service)

        event = json.dumps({
            "type": "level_up",
            "data": {"new_level": 5},
        })

        await dispatcher._handle_event(event)
        mock_push_service.send_to_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_template_vars_skipped(self, mock_redis, mock_push_service):
        """テンプレート変数不足はスキップ"""
        dispatcher = PushDispatcher(mock_redis, mock_push_service)

        event = json.dumps({
            "type": "level_up",
            "data": {"user_id": 123},  # new_levelが足りない
        })

        await dispatcher._handle_event(event)
        mock_push_service.send_to_user.assert_not_called()


class TestPushDispatcherLifecycle:
    """ライフサイクルテスト"""

    @pytest.mark.asyncio
    async def test_init_and_close(self, mock_push_service):
        """init/close/getの一連のライフサイクル"""
        from api.services import push_dispatcher as mod

        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub

        # listen()を即座にキャンセルさせる
        mock_pubsub.listen = MagicMock(return_value=AsyncIterStop())

        dispatcher = await mod.init_push_dispatcher(mock_redis, mock_push_service)
        assert dispatcher is not None
        assert mod.get_push_dispatcher() is dispatcher

        await mod.close_push_dispatcher()

        with pytest.raises(RuntimeError, match="未初期化"):
            mod.get_push_dispatcher()


class TestTemplatesComplete:
    """テンプレート定義チェック"""

    def test_all_templates_have_two_elements(self):
        """全テンプレートが(title, body)のタプル"""
        for event_type, template in TEMPLATES.items():
            assert isinstance(template, tuple), f"{event_type}: タプルではない"
            assert len(template) == 2, f"{event_type}: 要素数が2ではない"

    def test_expected_event_types(self):
        """期待するイベント種別が全て定義されている"""
        expected = {
            "level_up",
            "achievement_unlock",
            "pomodoro_complete",
            "insights_ready",
            "raid_join",
            "app_breach",
        }
        assert set(TEMPLATES.keys()) == expected


class AsyncIterStop:
    """即座にStopAsyncIterationを返すasync iterator"""

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration
