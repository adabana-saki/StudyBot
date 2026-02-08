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
        if self.redis:
            await self.redis.publish(channel, json.dumps(data, default=str))

    async def get(self, key: str) -> str | None:
        if self.redis:
            return await self.redis.get(key)
        return None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self.redis:
            await self.redis.set(key, value, ex=ex)

    async def delete(self, key: str) -> None:
        if self.redis:
            await self.redis.delete(key)

    async def zadd(self, key: str, mapping: dict, nx: bool = False) -> None:
        if self.redis:
            await self.redis.zadd(key, mapping, nx=nx)

    async def zrem(self, key: str, *members: str) -> None:
        if self.redis:
            await self.redis.zrem(key, *members)

    async def zrange(
        self, key: str, start: int = 0, end: int = -1, withscores: bool = False
    ) -> list:
        if self.redis:
            return await self.redis.zrange(key, start, end, withscores=withscores)
        return []

    async def expire(self, key: str, seconds: int) -> None:
        if self.redis:
            await self.redis.expire(key, seconds)

    async def keys(self, pattern: str) -> list[str]:
        """パターンに一致するキーを返す"""
        if self.redis:
            return await self.redis.keys(pattern)
        return []
