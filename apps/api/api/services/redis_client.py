"""API用 Redis クライアント"""

import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


async def init_redis(url: str) -> redis.Redis:
    """Redis接続初期化"""
    global _redis
    _redis = redis.from_url(url, decode_responses=True)
    await _redis.ping()
    logger.info("Redis接続成功")
    return _redis


async def close_redis() -> None:
    """Redis接続終了"""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis接続を閉じました")


def get_redis() -> redis.Redis:
    """Redis接続を取得"""
    if not _redis:
        raise RuntimeError("Redis未初期化")
    return _redis
