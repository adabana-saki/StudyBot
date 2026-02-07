"""学習プラン DB操作"""

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PlanRepository(BaseRepository):
    """学習プランのCRUD"""

    async def create_plan(
        self,
        user_id: int,
        subject: str,
        goal: str,
        deadline: datetime | None = None,
    ) -> dict:
        """学習プランを作成"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO study_plans (user_id, subject, goal, deadline)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                user_id,
                subject,
                goal,
                deadline,
            )
        return dict(row)

    async def get_active_plan(self, user_id: int) -> dict | None:
        """アクティブな学習プランを取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM study_plans
                WHERE user_id = $1 AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id,
            )
        return dict(row) if row else None

    async def get_plan_with_tasks(self, plan_id: int) -> dict:
        """プランとタスクを取得"""
        async with self.db_pool.acquire() as conn:
            plan_row = await conn.fetchrow(
                "SELECT * FROM study_plans WHERE id = $1",
                plan_id,
            )
            if not plan_row:
                return {}

            task_rows = await conn.fetch(
                """
                SELECT * FROM plan_tasks
                WHERE plan_id = $1
                ORDER BY order_index ASC
                """,
                plan_id,
            )
        return {
            "plan": dict(plan_row),
            "tasks": [dict(row) for row in task_rows],
        }

    async def add_task(
        self,
        plan_id: int,
        title: str,
        description: str = "",
        order_index: int = 0,
    ) -> dict:
        """タスクを追加"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO plan_tasks (plan_id, title, description, order_index)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                plan_id,
                title,
                description,
                order_index,
            )
        return dict(row)

    async def complete_task(self, task_id: int) -> dict | None:
        """タスクを完了にする"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE plan_tasks
                SET status = 'completed', completed_at = $2
                WHERE id = $1 AND status != 'completed'
                RETURNING *
                """,
                task_id,
                datetime.now(UTC),
            )
        return dict(row) if row else None

    async def get_plan_progress(self, plan_id: int) -> dict:
        """プランの進捗を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed
                FROM plan_tasks
                WHERE plan_id = $1
                """,
                plan_id,
            )
        total = row["total"] if row else 0
        completed = row["completed"] if row else 0
        percentage = round((completed / total * 100) if total > 0 else 0, 1)
        return {
            "total": total,
            "completed": completed,
            "percentage": percentage,
        }

    async def update_ai_feedback(self, plan_id: int, feedback: str) -> None:
        """AIフィードバックを更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE study_plans
                SET ai_feedback = $2
                WHERE id = $1
                """,
                plan_id,
                feedback,
            )
