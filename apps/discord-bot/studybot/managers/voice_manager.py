"""VC勉強追跡 ビジネスロジック"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from studybot.repositories.voice_repository import VoiceRepository

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


class VoiceManager:
    """VC勉強セッションの管理"""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self.repository = VoiceRepository(db_pool)
        self._sessions: dict[int, dict] = {}  # user_id -> session info

    def start_session(self, user_id: int, guild_id: int, channel_id: int) -> None:
        """VCセッション開始を記録"""
        self._sessions[user_id] = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "started_at": datetime.now(UTC),
        }
        logger.info("VC勉強セッション開始: user=%d, channel=%d", user_id, channel_id)

    async def end_session(self, user_id: int, min_minutes: int = 5) -> dict | None:
        """VCセッション終了を記録、DB保存"""
        session = self._sessions.pop(user_id, None)
        if not session:
            return None

        ended_at = datetime.now(UTC)
        duration_seconds = (ended_at - session["started_at"]).total_seconds()
        duration_minutes = int(duration_seconds / 60)

        if duration_minutes < min_minutes:
            logger.debug(
                "VC勉強セッションが短すぎます: %d分 (最低%d分)", duration_minutes, min_minutes
            )
            return None

        await self.repository.ensure_user(user_id)
        session_id = await self.repository.save_vc_session(
            user_id=user_id,
            guild_id=session["guild_id"],
            channel_id=session["channel_id"],
            started_at=session["started_at"],
            ended_at=ended_at,
            duration_minutes=duration_minutes,
        )

        return {
            "session_id": session_id,
            "user_id": user_id,
            "guild_id": session["guild_id"],
            "channel_id": session["channel_id"],
            "duration_minutes": duration_minutes,
        }

    def get_active_sessions(self) -> dict[int, dict]:
        """アクティブなVCセッション一覧を取得"""
        return dict(self._sessions)

    def is_tracking(self, user_id: int) -> bool:
        """ユーザーが追跡中か確認"""
        return user_id in self._sessions

    async def get_stats(self, user_id: int, guild_id: int, days: int = 30) -> dict:
        """VC勉強統計を取得"""
        return await self.repository.get_vc_stats(user_id, guild_id, days)

    async def get_ranking(self, guild_id: int, days: int = 30) -> list[dict]:
        """VC勉強ランキングを取得"""
        return await self.repository.get_vc_ranking(guild_id, days)

    async def get_server_settings(self, guild_id: int) -> dict | None:
        """サーバー設定を取得"""
        return await self.repository.get_server_settings(guild_id)
