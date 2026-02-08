"""SSEイベントストリーム管理"""

import asyncio
import json
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)

EVENTS_CHANNEL = "studybot:events"
SESSIONS_CHANNEL = "studybot:sessions"


class EventStreamManager:
    """Redis Pub/Sub → per-guild SSEキュー fan-out"""

    def __init__(self, redis_conn: redis.Redis) -> None:
        self.redis = redis_conn
        self.pubsub: redis.client.PubSub | None = None
        self._subscribers: dict[int, list[asyncio.Queue]] = {}
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(EVENTS_CHANNEL, SESSIONS_CHANNEL)
        self._task = asyncio.create_task(self._listen())
        logger.info("EventStreamManager開始")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.aclose()
        logger.info("EventStreamManager停止")

    async def _listen(self) -> None:
        try:
            async for message in self.pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    guild_id = data.get("data", {}).get("guild_id")
                    if guild_id:
                        await self._fan_out(int(guild_id), data)
                except (json.JSONDecodeError, KeyError):
                    logger.warning("不正なイベントデータ受信")
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("EventStreamManager listener エラー")

    async def _fan_out(self, guild_id: int, data: dict) -> None:
        queues = self._subscribers.get(guild_id, [])
        dead = []
        for q in queues:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            queues.remove(q)

    def subscribe(self, guild_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.setdefault(guild_id, []).append(q)
        return q

    def unsubscribe(self, guild_id: int, queue: asyncio.Queue) -> None:
        queues = self._subscribers.get(guild_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues and guild_id in self._subscribers:
            del self._subscribers[guild_id]


# Module-level singleton
_manager: EventStreamManager | None = None


async def init_event_stream(redis_conn: redis.Redis) -> EventStreamManager:
    global _manager
    _manager = EventStreamManager(redis_conn)
    await _manager.start()
    return _manager


async def close_event_stream() -> None:
    global _manager
    if _manager:
        await _manager.stop()
        _manager = None


def get_event_stream() -> EventStreamManager:
    if not _manager:
        raise RuntimeError("EventStreamManager未初期化")
    return _manager
