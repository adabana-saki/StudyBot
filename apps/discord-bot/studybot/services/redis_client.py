"""Redis クライアント"""

import json
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 非同期クライアント"""

    def __init__(self, url: str) -> None:
        self.url = url
        self.redis: redis.Redis | None = None

    async def connect(self) -> None:
        self.redis = redis.from_url(self.url, decode_responses=True)
        await self.redis.ping()
        logger.info("Redis接続成功")

    async def close(self) -> None:
        if self.redis:
            await self.redis.aclose()
            logger.info("Redis接続を閉じました")

    async def publish(self, channel: str, data: dict) -> None:
        if not self.redis:
            return
        try:
            await self.redis.publish(channel, json.dumps(data, default=str))
        except Exception:
            logger.warning("Redis publish failed for channel=%s", channel, exc_info=True)

    async def get(self, key: str) -> str | None:
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception:
            logger.warning("Redis get failed for key=%s", key, exc_info=True)
            return None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if not self.redis:
            return
        try:
            await self.redis.set(key, value, ex=ex)
        except Exception:
            logger.warning("Redis set failed for key=%s", key, exc_info=True)

    async def delete(self, key: str) -> None:
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception:
            logger.warning("Redis delete failed for key=%s", key, exc_info=True)

    async def zadd(self, key: str, mapping: dict, nx: bool = False) -> None:
        if not self.redis:
            return
        try:
            await self.redis.zadd(key, mapping, nx=nx)
        except Exception:
            logger.warning("Redis zadd failed for key=%s", key, exc_info=True)

    async def zrem(self, key: str, *members: str) -> None:
        if not self.redis:
            return
        try:
            await self.redis.zrem(key, *members)
        except Exception:
            logger.warning("Redis zrem failed for key=%s", key, exc_info=True)

    async def zrange(
        self, key: str, start: int = 0, end: int = -1, withscores: bool = False
    ) -> list:
        if not self.redis:
            return []
        try:
            return await self.redis.zrange(key, start, end, withscores=withscores)
        except Exception:
            logger.warning("Redis zrange failed for key=%s", key, exc_info=True)
            return []

    async def expire(self, key: str, seconds: int) -> None:
        if not self.redis:
            return
        try:
            await self.redis.expire(key, seconds)
        except Exception:
            logger.warning("Redis expire failed for key=%s", key, exc_info=True)

    async def keys(self, pattern: str) -> list[str]:
        """パターンに一致するキーを返す"""
        if not self.redis:
            return []
        try:
            return await self.redis.keys(pattern)
        except Exception:
            logger.warning("Redis keys failed for pattern=%s", pattern, exc_info=True)
            return []
