"""VC勉強セッション DB操作.

``vc_sessions`` テーブルへのセッション記録・統計取得と、
``server_settings`` テーブルのVC関連設定の読み書きを担当する。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from studybot.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class VoiceRepository(BaseRepository):
    """VC勉強セッション関連のCRUD.

    管理するテーブル:
        - ``vc_sessions``: ボイスチャンネルでの勉強セッション記録
        - ``server_settings``: VC追跡に関するサーバーごとの設定
    """

    async def save_vc_session(
        self,
        user_id: int,
        guild_id: int,
        channel_id: int,
        started_at: datetime,
        ended_at: datetime,
        duration_minutes: int,
    ) -> int:
        """VCセッションを ``vc_sessions`` テーブルに保存する。

        ``auto_logged`` フラグは常に ``TRUE`` で記録される。

        Args:
            user_id: DiscordユーザーID
            guild_id: DiscordサーバーID
            channel_id: ボイスチャンネルID
            started_at: セッション開始日時 (UTC)
            ended_at: セッション終了日時 (UTC)
            duration_minutes: セッション長（分）

        Returns:
            挿入された行の ``id`` カラム値
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchval(
                """
                INSERT INTO vc_sessions
                    (user_id, guild_id, channel_id, started_at, ended_at,
                     duration_minutes, auto_logged)
                VALUES ($1, $2, $3, $4, $5, $6, TRUE)
                RETURNING id
                """,
                user_id,
                guild_id,
                channel_id,
                started_at,
                ended_at,
                duration_minutes,
            )
        return row

    async def get_vc_stats(self, user_id: int, guild_id: int, days: int = 30) -> dict:
        """指定期間のVC勉強統計を取得する。

        Args:
            user_id: DiscordユーザーID
            guild_id: DiscordサーバーID
            days: 集計対象の日数（デフォルト30日）

        Returns:
            ``total_minutes``, ``session_count``, ``avg_minutes`` を含む辞書。
            データが存在しない場合はすべて 0 の辞書を返す。
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(duration_minutes), 0) as total_minutes,
                    COUNT(*) as session_count,
                    COALESCE(AVG(duration_minutes), 0) as avg_minutes
                FROM vc_sessions
                WHERE user_id = $1 AND guild_id = $2
                  AND started_at >= CURRENT_TIMESTAMP - make_interval(days => $3)
                """,
                user_id,
                guild_id,
                days,
            )
        return dict(row) if row else {"total_minutes": 0, "session_count": 0, "avg_minutes": 0}

    async def get_vc_ranking(self, guild_id: int, days: int = 30, limit: int = 10) -> list[dict]:
        """指定期間のVC勉強ランキングを取得する。

        ``vc_sessions`` と ``users`` をJOINし、合計学習時間の降順で返す。

        Args:
            guild_id: DiscordサーバーID
            days: 集計対象の日数（デフォルト30日）
            limit: 返却する最大件数（デフォルト10件）

        Returns:
            ``user_id``, ``username``, ``total_minutes``, ``session_count``
            を含む辞書のリスト。
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT vs.user_id, u.username,
                       SUM(vs.duration_minutes) as total_minutes,
                       COUNT(*) as session_count
                FROM vc_sessions vs
                JOIN users u ON u.user_id = vs.user_id
                WHERE vs.guild_id = $1
                  AND vs.started_at >= CURRENT_TIMESTAMP - make_interval(days => $2)
                GROUP BY vs.user_id, u.username
                ORDER BY total_minutes DESC
                LIMIT $3
                """,
                guild_id,
                days,
                limit,
            )
        return [dict(row) for row in rows]

    async def get_server_settings(self, guild_id: int) -> dict | None:
        """サーバー設定を ``server_settings`` テーブルから取得する。

        Args:
            guild_id: DiscordサーバーID

        Returns:
            設定が存在する場合はその辞書、存在しない場合は ``None``。
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM server_settings WHERE guild_id = $1",
                guild_id,
            )
        return dict(row) if row else None

    # サーバー設定テーブルの更新可能カラム
    _ALLOWED_COLUMNS = frozenset(
        {
            "study_channels",
            "vc_channels",
            "admin_role_id",
            "nudge_enabled",
            "vc_tracking_enabled",
            "min_vc_minutes",
        }
    )

    async def upsert_server_settings(self, guild_id: int, **kwargs: object) -> dict:
        """サーバー設定を更新または作成する。

        カラム名はホワイトリストで検証され、不正なキーは無視される。

        Args:
            guild_id: サーバーID
            **kwargs: 更新するカラム名と値のペア

        Returns:
            更新後のサーバー設定辞書
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO server_settings (guild_id) VALUES ($1)"
                " ON CONFLICT (guild_id) DO NOTHING",
                guild_id,
            )
            sets = []
            params: list[object] = [guild_id]
            idx = 2
            for key, value in kwargs.items():
                if key not in self._ALLOWED_COLUMNS:
                    logger.warning("不正な設定キーを無視: %s", key)
                    continue
                sets.append(f"{key} = ${idx}")  # noqa: S608
                params.append(value)
                idx += 1
            if sets:
                sets.append(f"updated_at = ${idx}")
                params.append(datetime.now(UTC))
                set_clause = ", ".join(sets)
                query = (
                    f"UPDATE server_settings SET {set_clause}"  # noqa: S608
                    " WHERE guild_id = $1 RETURNING *"
                )
                row = await conn.fetchrow(query, *params)
                return dict(row) if row else {}
            row = await conn.fetchrow(
                "SELECT * FROM server_settings WHERE guild_id = $1",
                guild_id,
            )
            return dict(row) if row else {}
