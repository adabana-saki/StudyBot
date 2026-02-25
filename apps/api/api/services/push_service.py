"""FCMプッシュ通知サービス

Firebase Admin SDKを使用してFCMプッシュ通知を送信する。
firebase-credentials.jsonが存在しない場合はgraceful degradation（警告のみ）。
"""

import asyncio
import json
import logging
from functools import partial
from pathlib import Path

import asyncpg

from api.config import settings

logger = logging.getLogger(__name__)


class PushNotificationService:
    """FCMプッシュ通知送信サービス"""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self.db_pool = db_pool
        self._initialized = False
        self._app = None

    async def initialize(self) -> None:
        """Firebase Admin SDK初期化"""
        creds_path = settings.FIREBASE_CREDENTIALS_PATH
        if not creds_path or not Path(creds_path).exists():
            logger.warning(
                "Firebase credentials未設定 (%s) — プッシュ通知は無効です",
                creds_path or "(空)",
            )
            return

        try:
            import firebase_admin
            from firebase_admin import credentials

            cred = credentials.Certificate(creds_path)
            self._app = firebase_admin.initialize_app(cred)
            self._initialized = True
            logger.info("Firebase Admin SDK初期化完了")
        except Exception:
            logger.exception("Firebase Admin SDK初期化失敗")

    async def close(self) -> None:
        """Firebase Admin SDKクリーンアップ"""
        if self._app:
            try:
                import firebase_admin

                firebase_admin.delete_app(self._app)
            except Exception:
                pass
            self._app = None
            self._initialized = False

    async def send_to_user(
        self,
        user_id: int,
        title: str,
        body: str,
        data: dict | None = None,
        notification_type: str = "general",
    ) -> int:
        """ユーザーにプッシュ通知を送信

        Args:
            user_id: 送信先ユーザーID
            title: 通知タイトル
            body: 通知本文
            data: カスタムデータ（ディープリンクなど）
            notification_type: 通知種別

        Returns:
            送信成功数
        """
        if not self._initialized:
            logger.debug("Firebase未初期化のためプッシュ通知スキップ (user_id=%s)", user_id)
            return 0

        # アクティブなデバイストークンを取得
        async with self.db_pool.acquire() as conn:
            tokens = await conn.fetch(
                """
                SELECT id, device_token, platform
                FROM device_tokens
                WHERE user_id = $1 AND is_active = TRUE
                """,
                user_id,
            )

        if not tokens:
            return 0

        from firebase_admin import messaging

        sent_count = 0
        invalid_token_ids: list[int] = []
        data_str = {k: str(v) for k, v in (data or {}).items()}

        loop = asyncio.get_event_loop()

        for token_row in tokens:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data_str,
                token=token_row["device_token"],
            )

            try:
                # messaging.send()は同期ブロッキング → executorで実行
                await loop.run_in_executor(None, partial(messaging.send, message))
                sent_count += 1
            except messaging.UnregisteredError:
                logger.info(
                    "無効なFCMトークン検出 (token_id=%s) — 自動無効化",
                    token_row["id"],
                )
                invalid_token_ids.append(token_row["id"])
            except Exception:
                logger.exception(
                    "FCM送信失敗 (token_id=%s)",
                    token_row["id"],
                )

        # 無効トークンを自動無効化
        if invalid_token_ids:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE device_tokens
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE id = ANY($1::int[])
                    """,
                    invalid_token_ids,
                )

        # 通知ログに記録
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO notification_logs (user_id, type, title, body, data)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                notification_type,
                title,
                body,
                json.dumps(data) if data else None,
            )

        logger.info(
            "プッシュ通知送信完了: user_id=%s, type=%s, sent=%d/%d",
            user_id,
            notification_type,
            sent_count,
            len(tokens),
        )
        return sent_count


# Module-level singleton
_service: PushNotificationService | None = None


async def init_push_service(db_pool: asyncpg.Pool) -> PushNotificationService:
    """プッシュ通知サービス初期化"""
    global _service
    _service = PushNotificationService(db_pool)
    await _service.initialize()
    return _service


async def close_push_service() -> None:
    """プッシュ通知サービス終了"""
    global _service
    if _service:
        await _service.close()
        _service = None


def get_push_service() -> PushNotificationService:
    """プッシュ通知サービス取得"""
    if not _service:
        raise RuntimeError("PushNotificationService未初期化")
    return _service
