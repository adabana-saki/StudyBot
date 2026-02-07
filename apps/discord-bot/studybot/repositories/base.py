"""リポジトリ基底クラス"""

import logging

import asyncpg

logger = logging.getLogger(__name__)


class BaseRepository:
    """全リポジトリの基底クラス"""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self.db_pool = db_pool

    async def ensure_user(self, user_id: int, username: str = "") -> None:
        """ユーザーが存在しない場合は作成"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, username)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET username = $2
                """,
                user_id,
                username,
            )
