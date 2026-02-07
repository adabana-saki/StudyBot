"""データベース接続管理"""

import logging

import asyncpg

from api.config import settings

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    """接続プール初期化"""
    global pool
    db_url = settings.database_url_fixed
    if not db_url:
        raise RuntimeError("DATABASE_URL が設定されていません")

    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5, command_timeout=30)
    logger.info("データベース接続プール作成完了")
    return pool


async def close_pool() -> None:
    """接続プール終了"""
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("データベース接続プール終了")


def get_pool() -> asyncpg.Pool:
    """接続プール取得"""
    if not pool:
        raise RuntimeError("データベース未初期化")
    return pool
