"""フォーカスモード ビジネスロジック"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from studybot.config.constants import FOCUS_DEFAULTS
from studybot.repositories.focus_repository import FocusRepository

logger = logging.getLogger(__name__)


class FocusManager:
    """フォーカスモードの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = FocusRepository(db_pool)
        # メモリ内セッション状態 (user_id -> session_info)
        self.active_sessions: dict[int, dict] = {}
        self._lock = asyncio.Lock()

    async def start_focus(
        self,
        user_id: int,
        username: str,
        guild_id: int,
        duration_minutes: int = FOCUS_DEFAULTS["default_duration"],
    ) -> dict:
        """フォーカスセッションを開始"""
        async with self._lock:
            await self.repository.ensure_user(user_id, username)

            # 既存のアクティブセッションをチェック
            if user_id in self.active_sessions:
                return {"error": "既にフォーカスセッションが進行中です。先に終了してください。"}

            # DB上のアクティブセッションもチェック
            active = await self.repository.get_active_session(user_id)
            if active:
                return {"error": "既にフォーカスセッションが進行中です。先に終了してください。"}

            # 時間のバリデーション
            min_dur = FOCUS_DEFAULTS["min_duration"]
            max_dur = FOCUS_DEFAULTS["max_duration"]
            if duration_minutes < min_dur or duration_minutes > max_dur:
                return {"error": f"フォーカス時間は{min_dur}〜{max_dur}分で指定してください。"}

            # DBにセッションを作成
            session = await self.repository.create_session(user_id, guild_id, duration_minutes)

            now = datetime.now(UTC)
            end_time = now + timedelta(minutes=duration_minutes)

            # メモリ内にセッション情報を保存
            self.active_sessions[user_id] = {
                "session_id": session["id"],
                "guild_id": guild_id,
                "duration_minutes": duration_minutes,
                "started_at": now,
                "end_time": end_time,
                "whitelisted_channels": [],
            }

            return {
                "session_id": session["id"],
                "duration": duration_minutes,
                "end_time": end_time,
            }

    async def add_whitelist(self, user_id: int, channel_id: int) -> dict:
        """アクティブセッションにホワイトリストチャンネルを追加"""
        session = self.active_sessions.get(user_id)
        if not session:
            return {"error": "アクティブなフォーカスセッションがありません。"}

        if channel_id in session["whitelisted_channels"]:
            return {"error": "このチャンネルは既にホワイトリストに追加されています。"}

        # メモリ内を更新
        session["whitelisted_channels"].append(channel_id)

        # DBを更新
        await self.repository.add_whitelist_channel(session["session_id"], channel_id)

        return {
            "success": True,
            "channel_id": channel_id,
            "whitelist_count": len(session["whitelisted_channels"]),
        }

    async def end_focus(self, user_id: int) -> dict:
        """フォーカスセッションを終了"""
        async with self._lock:
            session = self.active_sessions.pop(user_id, None)
            if not session:
                return {"error": "アクティブなフォーカスセッションがありません。"}

            now = datetime.now(UTC)
            actual_seconds = int((now - session["started_at"]).total_seconds())
            actual_minutes = actual_seconds // 60

            # DBのセッションを完了に更新
            await self.repository.end_session(session["session_id"])

            # 予定時間を達成したかチェック
            completed = actual_minutes >= session["duration_minutes"]

            return {
                "session_id": session["session_id"],
                "duration_planned": session["duration_minutes"],
                "duration_actual": actual_minutes,
                "completed": completed,
            }

    def get_status(self, user_id: int) -> dict | None:
        """現在のフォーカスセッション状態を取得"""
        session = self.active_sessions.get(user_id)
        if not session:
            return None

        now = datetime.now(UTC)
        elapsed = (now - session["started_at"]).total_seconds()
        total = session["duration_minutes"] * 60
        remaining = max(0, total - elapsed)
        progress = min(1.0, elapsed / total) if total > 0 else 1.0

        return {
            "session_id": session["session_id"],
            "duration_minutes": session["duration_minutes"],
            "remaining_seconds": int(remaining),
            "progress": progress,
            "whitelisted_channels": session["whitelisted_channels"],
            "started_at": session["started_at"],
            "end_time": session["end_time"],
        }

    async def check_sessions(self) -> list[dict]:
        """全アクティブセッションをチェックし、期限切れを返す"""
        async with self._lock:
            now = datetime.now(UTC)
            expired = []

            expired_user_ids = [
                user_id
                for user_id, session in self.active_sessions.items()
                if now >= session["end_time"]
            ]

            for user_id in expired_user_ids:
                session = self.active_sessions.pop(user_id, None)
                if not session:
                    continue

                # DBのセッションを完了に更新
                await self.repository.end_session(session["session_id"])

                expired.append(
                    {
                        "user_id": user_id,
                        "session_id": session["session_id"],
                        "duration_minutes": session["duration_minutes"],
                        "guild_id": session["guild_id"],
                    }
                )

            return expired
