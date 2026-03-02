"""PushNotificationService テスト"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import MockAsyncCtx


def _sync_executor(_, fn, *args):
    """run_in_executorのモック: 同期関数をそのまま実行してコルーチンとして返す"""

    async def _run():
        return fn()

    return _run()


@pytest.fixture
def mock_db_pool():
    """モックDB接続プール"""
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value = MockAsyncCtx(conn)
    return pool, conn


@pytest.fixture
def push_service(mock_db_pool):
    """PushNotificationService（Firebase未初期化状態）"""
    from api.services.push_service import PushNotificationService

    pool, _ = mock_db_pool
    svc = PushNotificationService(pool)
    return svc


class TestPushServiceInitialization:
    """Firebase初期化テスト"""

    @pytest.mark.asyncio
    async def test_initialize_no_credentials(self, push_service):
        """credentials未設定時はgraceful degradation"""
        with patch("api.services.push_service.settings") as mock_settings:
            mock_settings.FIREBASE_CREDENTIALS_PATH = ""
            await push_service.initialize()
            assert push_service._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_missing_file(self, push_service):
        """credentialsファイルが存在しない場合はgraceful degradation"""
        with patch("api.services.push_service.settings") as mock_settings:
            mock_settings.FIREBASE_CREDENTIALS_PATH = "/nonexistent/path.json"
            await push_service.initialize()
            assert push_service._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_success(self, push_service):
        """Firebase初期化成功"""
        with (
            patch("api.services.push_service.settings") as mock_settings,
            patch("api.services.push_service.Path") as mock_path,
            patch("firebase_admin.credentials.Certificate") as mock_cert,
            patch("firebase_admin.initialize_app") as mock_init,
        ):
            mock_settings.FIREBASE_CREDENTIALS_PATH = "/app/creds.json"
            mock_path.return_value.exists.return_value = True
            mock_init.return_value = MagicMock()

            await push_service.initialize()
            assert push_service._initialized is True
            mock_cert.assert_called_once_with("/app/creds.json")
            mock_init.assert_called_once()


class TestPushServiceSend:
    """送信テスト"""

    @pytest.mark.asyncio
    async def test_send_when_not_initialized(self, push_service):
        """未初期化状態では送信スキップ"""
        result = await push_service.send_to_user(user_id=123, title="Test", body="Body")
        assert result == 0

    @pytest.mark.asyncio
    async def test_send_no_tokens(self, push_service, mock_db_pool):
        """アクティブトークンなし"""
        _, conn = mock_db_pool
        push_service._initialized = True
        conn.fetch.return_value = []

        result = await push_service.send_to_user(user_id=123, title="Test", body="Body")
        assert result == 0

    @pytest.mark.asyncio
    async def test_send_success(self, push_service, mock_db_pool):
        """FCM送信成功"""
        _, conn = mock_db_pool
        push_service._initialized = True

        conn.fetch.return_value = [
            {"id": 1, "device_token": "token-aaa", "platform": "android"},
            {"id": 2, "device_token": "token-bbb", "platform": "android"},
        ]

        loop = asyncio.get_event_loop()
        with (
            patch("firebase_admin.messaging.send") as mock_send,
            patch.object(loop, "run_in_executor", side_effect=_sync_executor),
        ):
            mock_send.return_value = "projects/test/messages/12345"

            result = await push_service.send_to_user(
                user_id=123,
                title="レベルアップ!",
                body="レベル5になりました!",
                data={"event_type": "level_up"},
                notification_type="level_up",
            )

        assert result == 2
        assert mock_send.call_count == 2
        conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_send_unregistered_error(self, push_service, mock_db_pool):
        """UnregisteredError時にトークン自動無効化"""
        _, conn = mock_db_pool
        push_service._initialized = True

        conn.fetch.return_value = [
            {"id": 1, "device_token": "valid-token", "platform": "android"},
            {"id": 2, "device_token": "invalid-token", "platform": "android"},
        ]

        loop = asyncio.get_event_loop()
        with (
            patch("firebase_admin.messaging") as mock_messaging,
            patch.object(loop, "run_in_executor", side_effect=_sync_executor),
        ):
            mock_messaging.Message = MagicMock()
            mock_messaging.Notification = MagicMock()
            mock_messaging.UnregisteredError = type("UnregisteredError", (Exception,), {})
            mock_messaging.send.side_effect = [
                "ok",
                mock_messaging.UnregisteredError("unregistered"),
            ]

            result = await push_service.send_to_user(user_id=123, title="Test", body="Body")

        assert result == 1
        # 無効トークン無効化 + 通知ログ記録
        assert conn.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_logs_notification(self, push_service, mock_db_pool):
        """送信後にnotification_logsに記録"""
        _, conn = mock_db_pool
        push_service._initialized = True

        conn.fetch.return_value = [
            {"id": 1, "device_token": "token-aaa", "platform": "android"},
        ]

        loop = asyncio.get_event_loop()
        with (
            patch("firebase_admin.messaging.send"),
            patch.object(loop, "run_in_executor", side_effect=_sync_executor),
        ):
            await push_service.send_to_user(
                user_id=42,
                title="テスト通知",
                body="本文",
                data={"key": "value"},
                notification_type="test",
            )

        last_call = conn.execute.call_args_list[-1]
        sql = last_call[0][0]
        assert "notification_logs" in sql
        assert last_call[0][1] == 42
        assert last_call[0][2] == "test"
        assert last_call[0][3] == "テスト通知"
        assert last_call[0][4] == "本文"
        assert json.loads(last_call[0][5]) == {"key": "value"}


class TestPushServiceModuleFunctions:
    """モジュールレベル関数テスト"""

    @pytest.mark.asyncio
    async def test_init_and_close(self, mock_db_pool):
        """init/close/getの一連のライフサイクル"""
        from api.services import push_service as mod

        pool, _ = mock_db_pool

        with patch.object(mod.PushNotificationService, "initialize", new_callable=AsyncMock):
            svc = await mod.init_push_service(pool)
            assert svc is not None
            assert mod.get_push_service() is svc

        with patch.object(mod.PushNotificationService, "close", new_callable=AsyncMock):
            await mod.close_push_service()

        with pytest.raises(RuntimeError, match="未初期化"):
            mod.get_push_service()
