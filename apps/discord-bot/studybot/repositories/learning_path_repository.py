"""ラーニングパスリポジトリ"""

import logging

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class LearningPathRepository(BaseRepository):
    """learning_paths / path_milestones テーブル操作"""

    async def enroll_user(self, user_id: int, path_id: str) -> dict:
        """ユーザーをラーニングパスに登録"""
        async with self.db_pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO learning_paths (user_id, path_id)
                    VALUES ($1, $2)
                    RETURNING id, user_id, path_id, current_milestone,
                              completed, enrolled_at, completed_at
                    """,
                    user_id,
                    path_id,
                )
                return dict(row) if row else {}
            except Exception:
                logger.debug(
                    "ラーニングパス登録失敗 (user=%d, path=%s)",
                    user_id,
                    path_id,
                    exc_info=True,
                )
                return {"error": "既に登録済みです"}

    async def get_user_path(self, user_id: int, path_id: str) -> dict | None:
        """ユーザーの特定パス登録情報を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, path_id, current_milestone,
                       completed, enrolled_at, completed_at
                FROM learning_paths
                WHERE user_id = $1 AND path_id = $2
                """,
                user_id,
                path_id,
            )
            return dict(row) if row else None

    async def get_user_paths(self, user_id: int) -> list[dict]:
        """ユーザーの全登録パスを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, path_id, current_milestone,
                       completed, enrolled_at, completed_at
                FROM learning_paths
                WHERE user_id = $1
                ORDER BY enrolled_at DESC
                """,
                user_id,
            )
            return [dict(r) for r in rows]

    async def complete_milestone(
        self, user_id: int, path_id: str, milestone_index: int
    ) -> dict:
        """マイルストーンを完了としてマーク"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # マイルストーン記録を挿入
                try:
                    await conn.execute(
                        """
                        INSERT INTO path_milestones
                            (user_id, path_id, milestone_index)
                        VALUES ($1, $2, $3)
                        """,
                        user_id,
                        path_id,
                        milestone_index,
                    )
                except Exception:
                    logger.debug(
                        "マイルストーン既に完了 (user=%d, path=%s, idx=%d)",
                        user_id,
                        path_id,
                        milestone_index,
                        exc_info=True,
                    )
                    return {"error": "このマイルストーンは既に完了しています"}

                # current_milestone を更新
                await conn.execute(
                    """
                    UPDATE learning_paths
                    SET current_milestone = $3
                    WHERE user_id = $1 AND path_id = $2
                    """,
                    user_id,
                    path_id,
                    milestone_index + 1,
                )

                return {
                    "user_id": user_id,
                    "path_id": path_id,
                    "milestone_index": milestone_index,
                }

    async def mark_path_completed(self, user_id: int, path_id: str) -> None:
        """パスを完了としてマーク"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE learning_paths
                SET completed = TRUE, completed_at = NOW()
                WHERE user_id = $1 AND path_id = $2
                """,
                user_id,
                path_id,
            )

    async def get_path_progress(self, user_id: int, path_id: str) -> dict:
        """パスの進捗（完了マイルストーン数）を取得"""
        async with self.db_pool.acquire() as conn:
            completed_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM path_milestones
                WHERE user_id = $1 AND path_id = $2
                """,
                user_id,
                path_id,
            )
            return {
                "user_id": user_id,
                "path_id": path_id,
                "completed": completed_count or 0,
            }
