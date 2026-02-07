"""To-Do管理 ビジネスロジック"""

import logging
from datetime import datetime

from studybot.repositories.todo_repository import TodoRepository

logger = logging.getLogger(__name__)


class TodoManager:
    """タスク管理のビジネスロジック"""

    def __init__(self, db_pool) -> None:
        self.repository = TodoRepository(db_pool)

    async def add_todo(
        self,
        user_id: int,
        username: str,
        guild_id: int,
        title: str,
        priority: int = 2,
        deadline: datetime | None = None,
    ) -> int:
        """タスクを追加"""
        await self.repository.ensure_user(user_id, username)
        return await self.repository.create_todo(user_id, guild_id, title, priority, deadline)

    async def list_todos(
        self,
        user_id: int,
        guild_id: int,
        status: str | None = None,
    ) -> list[dict]:
        """タスク一覧を取得"""
        return await self.repository.get_todos(user_id, guild_id, status)

    async def complete_todo(self, todo_id: int, user_id: int) -> dict | None:
        """タスクを完了"""
        return await self.repository.complete_todo(todo_id, user_id)

    async def delete_todo(self, todo_id: int, user_id: int) -> bool:
        """タスクを削除"""
        return await self.repository.delete_todo(todo_id, user_id)

    async def get_overdue(self, guild_id: int) -> list[dict]:
        """期限切れタスクを取得"""
        return await self.repository.get_overdue_todos(guild_id)

    async def get_upcoming(self, guild_id: int, hours: int = 24) -> list[dict]:
        """期限が近いタスクを取得"""
        return await self.repository.get_upcoming_todos(guild_id, hours)
