"""管理者 DB操作.

サーバー全体の統計取得、ユーザーデータのリセット、
およびサーバー設定の更新など管理者向け操作を提供する。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AdminRepository(BaseRepository):
    """管理者関連のCRUD.

    サーバー統計の集計、ユーザーデータのリセット、
    および ``server_settings`` テーブルの更新操作を提供する。
    """

    async def get_server_stats(self, guild_id: int) -> dict:
        """サーバー全体の統計を ``study_logs``, ``todos``, ``study_raids`` から集計する。

        Args:
            guild_id: DiscordサーバーID

        Returns:
            以下のキーを含む辞書:
                - ``member_count``: DBに記録のあるユニークユーザー数
                - ``total_minutes``: 全期間の合計学習時間（分）
                - ``total_sessions``: 全期間のセッション数
                - ``weekly_minutes``: 直近7日間の合計学習時間（分）
                - ``weekly_active_members``: 直近7日間のアクティブメンバー数
                - ``tasks_completed``: 完了済みタスク数
                - ``raids_completed``: 完了済みレイド数
        """
        async with self.db_pool.acquire() as conn:
            # 総メンバー数（DBに記録のあるユーザー）
            member_count = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT user_id) FROM study_logs
                WHERE guild_id = $1
                """,
                guild_id,
            )

            # 総学習時間
            total_study = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(duration_minutes), 0) as total_minutes,
                    COUNT(*) as session_count
                FROM study_logs
                WHERE guild_id = $1
                """,
                guild_id,
            )

            # 今週の学習時間
            weekly = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(duration_minutes), 0) as total_minutes,
                    COUNT(DISTINCT user_id) as active_members
                FROM study_logs
                WHERE guild_id = $1
                  AND logged_at >= CURRENT_DATE - INTERVAL '7 days'
                """,
                guild_id,
            )

            # 完了タスク数
            task_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM todos
                WHERE guild_id = $1 AND status = 'completed'
                """,
                guild_id,
            )

            # レイド数
            raid_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM study_raids
                WHERE guild_id = $1 AND state = 'completed'
                """,
                guild_id,
            )

        return {
            "member_count": member_count or 0,
            "total_minutes": total_study["total_minutes"] if total_study else 0,
            "total_sessions": total_study["session_count"] if total_study else 0,
            "weekly_minutes": weekly["total_minutes"] if weekly else 0,
            "weekly_active_members": weekly["active_members"] if weekly else 0,
            "tasks_completed": task_count or 0,
            "raids_completed": raid_count or 0,
        }

    async def reset_user_data(self, user_id: int) -> bool:
        """ユーザーデータをリセットする（XP・コイン・実績・インベントリ）。

        単一トランザクション内で以下のテーブルを操作する:
            - ``user_levels``: XP=0, レベル=1, ストリーク=0 にリセット
            - ``virtual_currency``: 残高・累計獲得・累計消費を 0 にリセット
            - ``user_inventory``: 全レコードを削除
            - ``user_achievements``: 全レコードを削除

        Args:
            user_id: DiscordユーザーID

        Returns:
            常に ``True``。
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE user_levels SET xp = 0, level = 1, streak_days = 0 WHERE user_id = $1",
                    user_id,
                )
                await conn.execute(
                    "UPDATE virtual_currency SET balance = 0,"
                    " total_earned = 0, total_spent = 0"
                    " WHERE user_id = $1",
                    user_id,
                )
                await conn.execute(
                    "DELETE FROM user_inventory WHERE user_id = $1",
                    user_id,
                )
                await conn.execute(
                    "DELETE FROM user_achievements WHERE user_id = $1",
                    user_id,
                )
        return True

    # サーバー設定テーブルの更新可能カラム
    _ALLOWED_SETTING_COLUMNS = frozenset(
        {
            "study_channels",
            "vc_channels",
            "admin_role_id",
            "nudge_enabled",
            "vc_tracking_enabled",
            "min_vc_minutes",
        }
    )

    async def update_server_setting(self, guild_id: int, key: str, value: object) -> dict:
        """サーバー設定を更新する。

        Args:
            guild_id: サーバーID
            key: 更新するカラム名（ホワイトリスト検証済み）
            value: 設定値

        Returns:
            更新後のサーバー設定辞書

        Raises:
            ValueError: 許可されていないカラム名が指定された場合
        """
        if key not in self._ALLOWED_SETTING_COLUMNS:
            raise ValueError(f"許可されていない設定キー: {key}")

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO server_settings (guild_id) VALUES ($1)"
                " ON CONFLICT (guild_id) DO NOTHING",
                guild_id,
            )
            await conn.execute(
                f"UPDATE server_settings SET {key} = $2,"  # noqa: S608
                " updated_at = $3 WHERE guild_id = $1",
                guild_id,
                value,
                datetime.now(UTC),
            )
            row = await conn.fetchrow(
                "SELECT * FROM server_settings WHERE guild_id = $1",
                guild_id,
            )
        return dict(row) if row else {}
