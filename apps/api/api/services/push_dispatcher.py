"""プッシュ通知ディスパッチャー

Redis Pub/Subイベントを購読し、テンプレートに基づいてFCMプッシュ通知を発行する。
"""

import asyncio
import json
import logging

import redis.asyncio as redis

from api.services.push_service import PushNotificationService

logger = logging.getLogger(__name__)

EVENTS_CHANNEL = "studybot:events"

# イベント種別 → (タイトルテンプレート, 本文テンプレート) マッピング
TEMPLATES: dict[str, tuple[str, str]] = {
    "level_up": (
        "レベルアップ!",
        "レベル{new_level}になりました!",
    ),
    "achievement_unlock": (
        "{achievement_emoji} 実績解除!",
        "{achievement_name}を獲得!",
    ),
    "pomodoro_complete": (
        "ポモドーロ完了!",
        "{topic} - {work_minutes}分集中しました",
    ),
    "insights_ready": (
        "週間レポート完成",
        "新しいインサイトが{insights_count}件あります",
    ),
    "raid_join": (
        "レイド参加!",
        "{raid_topic}レイドにメンバーが参加",
    ),
    "app_breach": (
        "集中モード警告",
        "ブロック対象アプリが使用されました",
    ),
}


class PushDispatcher:
    """Redis Pub/Sub → FCMプッシュ通知ディスパッチャー"""

    def __init__(self, redis_conn: redis.Redis, push_service: PushNotificationService) -> None:
        self.redis = redis_conn
        self.push_service = push_service
        self.pubsub: redis.client.PubSub | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Redis購読を開始"""
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(EVENTS_CHANNEL)
        self._task = asyncio.create_task(self._listen())
        logger.info("PushDispatcher開始")

    async def stop(self) -> None:
        """購読解除・タスクキャンセル"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.aclose()
        logger.info("PushDispatcher停止")

    async def _listen(self) -> None:
        """Redis Pub/Subメッセージを受信しプッシュ通知に変換"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    await self._handle_event(message["data"])
                except Exception:
                    logger.exception("PushDispatcher イベント処理エラー")
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("PushDispatcher listener エラー")

    async def _handle_event(self, raw_data: str | bytes) -> None:
        """単一イベントを処理"""
        data = json.loads(raw_data)
        event_type = data.get("type", "")
        event_data = data.get("data", {})
        user_id = event_data.get("user_id")

        if not user_id:
            return

        template = TEMPLATES.get(event_type)
        if not template:
            return

        title_template, body_template = template

        try:
            title = title_template.format(**event_data)
            body = body_template.format(**event_data)
        except KeyError as e:
            logger.warning(
                "テンプレート変数不足: type=%s, missing=%s",
                event_type,
                e,
            )
            return

        await self.push_service.send_to_user(
            user_id=int(user_id),
            title=title,
            body=body,
            data={"event_type": event_type, **event_data},
            notification_type=event_type,
        )


# Module-level singleton
_dispatcher: PushDispatcher | None = None


async def init_push_dispatcher(
    redis_conn: redis.Redis, push_service: PushNotificationService
) -> PushDispatcher:
    """PushDispatcher初期化"""
    global _dispatcher
    _dispatcher = PushDispatcher(redis_conn, push_service)
    await _dispatcher.start()
    return _dispatcher


async def close_push_dispatcher() -> None:
    """PushDispatcher終了"""
    global _dispatcher
    if _dispatcher:
        await _dispatcher.stop()
        _dispatcher = None


def get_push_dispatcher() -> PushDispatcher:
    """PushDispatcher取得"""
    if not _dispatcher:
        raise RuntimeError("PushDispatcher未初期化")
    return _dispatcher
