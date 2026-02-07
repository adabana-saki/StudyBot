"""To-Do管理 DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TodoRepository(BaseRepository):
    """To-DoのCRUD"""

    async def create_todo(
        self,
        user_id: int,
        guild_id: int,
        title: str,
        priority: int = 2,
        deadline: datetime | None = None,
    ) -> int:
        """タスクを作成"""
        async with self.db_pool.acquire() as conn:
            todo_id = await conn.fetchval(
                """
                INSERT INTO todos (user_id, guild_id, title, priority, deadline)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                user_id,
                guild_id,
                title,
                priority,
                deadline,
            )
        return todo_id

    async def get_todos(
        self,
        user_id: int,
        guild_id: int,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """タスク一覧を取得"""
        query = """
            SELECT * FROM todos
            WHERE user_id = $1 AND guild_id = $2
        """
        params: list = [user_id, guild_id]

        if status:
            query += " AND status = $3"
            params.append(status)

        query += " ORDER BY priority ASC, deadline ASC NULLS LAST, created_at DESC"
        query += f" LIMIT {limit}"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    async def get_todo(self, todo_id: int, user_id: int) -> dict | None:
        """タスクを1件取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM todos WHERE id = $1 AND user_id = $2",
                todo_id,
                user_id,
            )
        return dict(row) if row else None

    async def complete_todo(self, todo_id: int, user_id: int) -> dict | None:
        """タスクを完了にする"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE todos
                SET status = 'completed', completed_at = $3
                WHERE id = $1 AND user_id = $2 AND status != 'completed'
                RETURNING *
                """,
                todo_id,
                user_id,
                datetime.now(UTC),
            )
        return dict(row) if row else None

    async def delete_todo(self, todo_id: int, user_id: int) -> bool:
        """タスクを削除"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM todos WHERE id = $1 AND user_id = $2",
                todo_id,
                user_id,
            )
        return result != "DELETE 0"

    async def get_overdue_todos(self, guild_id: int) -> list[dict]:
        """期限切れタスクを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM todos
                WHERE guild_id = $1
                  AND status = 'pending'
                  AND deadline IS NOT NULL
                  AND deadline < $2
                ORDER BY deadline ASC
                """,
                guild_id,
                datetime.now(UTC),
            )
        return [dict(row) for row in rows]

    async def get_upcoming_todos(self, guild_id: int, hours: int = 24) -> list[dict]:
        """期限が近いタスクを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM todos
                WHERE guild_id = $1
                  AND status = 'pending'
                  AND deadline IS NOT NULL
                  AND deadline BETWEEN $2 AND $2 + ($3 || ' hours')::interval
                ORDER BY deadline ASC
                """,
                guild_id,
                datetime.now(UTC),
                str(hours),
            )
        return [dict(row) for row in rows]

    async def get_completed_count(self, user_id: int, guild_id: int, days: int = 7) -> int:
        """完了タスク数を取得"""
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM todos
                WHERE user_id = $1 AND guild_id = $2
                  AND status = 'completed'
                  AND completed_at >= CURRENT_TIMESTAMP - ($3 || ' days')::interval
                """,
                user_id,
                guild_id,
                str(days),
            )
        return count or 0
