"""ロック設定 DB操作"""

import logging
import secrets
import string
from datetime import UTC, datetime, timedelta

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class LockSettingsRepository(BaseRepository):
    """ロック設定・アンロックコードのCRUD"""

    async def get_settings(self, user_id: int) -> dict | None:
        """ユーザーのロック設定を取得"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_lock_settings WHERE user_id = $1",
                user_id,
            )
        return dict(row) if row else None

    async def upsert_settings(
        self,
        user_id: int,
        default_unlock_level: int = 1,
        default_duration: int = 60,
        default_coin_bet: int = 0,
        block_categories: list[str] | None = None,
        custom_blocked_urls: list[str] | None = None,
    ) -> dict:
        """ロック設定を作成/更新"""
        async with self.db_pool.acquire() as conn:
            await self.ensure_user(user_id)
            row = await conn.fetchrow(
                """
                INSERT INTO user_lock_settings
                    (user_id, default_unlock_level, default_duration,
                     default_coin_bet, block_categories, custom_blocked_urls,
                     updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    default_unlock_level = $2,
                    default_duration = $3,
                    default_coin_bet = $4,
                    block_categories = $5,
                    custom_blocked_urls = $6,
                    updated_at = NOW()
                RETURNING *
                """,
                user_id,
                default_unlock_level,
                default_duration,
                default_coin_bet,
                block_categories or [],
                custom_blocked_urls or [],
            )
        return dict(row)

    async def create_unlock_code(
        self,
        user_id: int,
        session_id: int,
        code_type: str,
        code_length: int = 6,
        expires_minutes: int = 15,
    ) -> str:
        """アンロックコードを生成して保存"""
        if code_type == "confirmation":
            # 6桁数字
            code = "".join(secrets.choice(string.digits) for _ in range(code_length))
        else:
            # 英数字
            alphabet = string.ascii_uppercase + string.digits
            code = "".join(secrets.choice(alphabet) for _ in range(code_length))

        expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO unlock_codes
                    (user_id, session_id, code, code_type, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                session_id,
                code,
                code_type,
                expires_at,
            )
        return code

    async def get_valid_code(self, user_id: int, session_id: int, code: str) -> dict | None:
        """有効なアンロックコードを検証"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM unlock_codes
                WHERE user_id = $1
                  AND session_id = $2
                  AND code = $3
                  AND used = FALSE
                  AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id,
                session_id,
                code,
            )
        return dict(row) if row else None

    async def use_code(self, code_id: int) -> None:
        """コードを使用済みにする"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE unlock_codes SET used = TRUE WHERE id = $1",
                code_id,
            )

    async def create_code_request(self, user_id: int, session_id: int) -> dict:
        """コードリクエストを作成"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO code_requests (user_id, session_id, status)
                VALUES ($1, $2, 'pending')
                RETURNING *
                """,
                user_id,
                session_id,
            )
        return dict(row)

    async def get_pending_requests(self) -> list[dict]:
        """保留中のコードリクエストを取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT cr.*, pls.unlock_level, pls.lock_type
                FROM code_requests cr
                JOIN phone_lock_sessions pls ON pls.id = cr.session_id
                WHERE cr.status = 'pending'
                ORDER BY cr.created_at ASC
                """,
            )
        return [dict(row) for row in rows]

    async def fulfill_request(self, request_id: int) -> None:
        """コードリクエストをfulfilled状態に更新"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE code_requests SET status = 'fulfilled' WHERE id = $1",
                request_id,
            )

    async def get_lock_history(self, user_id: int, limit: int = 20) -> list[dict]:
        """ロックセッション履歴を取得"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM phone_lock_sessions
                WHERE user_id = $1
                ORDER BY started_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
        return [dict(row) for row in rows]
