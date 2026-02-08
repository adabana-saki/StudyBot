"""管理者 ビジネスロジック"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from studybot.repositories.admin_repository import AdminRepository

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


class AdminManager:
    """管理者機能の管理"""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self.repository = AdminRepository(db_pool)

    async def get_server_stats(self, guild_id: int) -> dict:
        """サーバー全体の統計を取得"""
        return await self.repository.get_server_stats(guild_id)

    async def reset_user(self, user_id: int) -> bool:
        """ユーザーデータをリセット"""
        return await self.repository.reset_user_data(user_id)

    async def update_setting(self, guild_id: int, key: str, value: object) -> dict:
        """サーバー設定を更新

        Args:
            guild_id: サーバーID
            key: 設定キー名
            value: 設定値

        Returns:
            更新後の設定情報を含むdict

        Raises:
            ValueError: リポジトリ層で無効なキーまたは値が検出された場合
        """
        return await self.repository.update_server_setting(guild_id, key, value)
