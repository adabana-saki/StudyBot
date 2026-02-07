"""ポモドーロタイマー ビジネスロジック"""

import logging
from datetime import UTC, datetime

from studybot.repositories.pomodoro_repository import PomodoroRepository

logger = logging.getLogger(__name__)


class PomodoroManager:
    """ポモドーロタイマーの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = PomodoroRepository(db_pool)
        # メモリ内タイマー状態 (user_id -> session_info)
        self.active_timers: dict[int, dict] = {}

    async def start_session(
        self,
        user_id: int,
        username: str,
        guild_id: int,
        channel_id: int,
        topic: str = "",
        work_minutes: int = 25,
        break_minutes: int = 5,
    ) -> dict:
        """セッション開始"""
        await self.repository.ensure_user(user_id, username)

        # 既存のアクティブセッションをチェック
        active = await self.repository.get_active_session(user_id)
        if active:
            return {"error": "既にアクティブなセッションがあります。先に停止してください。"}

        session_id = await self.repository.create_session(
            user_id, guild_id, channel_id, topic, work_minutes, break_minutes
        )

        now = datetime.now(UTC)
        self.active_timers[user_id] = {
            "session_id": session_id,
            "state": "working",
            "topic": topic,
            "work_minutes": work_minutes,
            "break_minutes": break_minutes,
            "started_at": now,
            "phase_started_at": now,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "accumulated_pause": 0,
        }

        return {
            "session_id": session_id,
            "topic": topic,
            "work_minutes": work_minutes,
            "break_minutes": break_minutes,
        }

    async def pause_session(self, user_id: int) -> dict:
        """セッション一時停止"""
        timer = self.active_timers.get(user_id)
        if not timer:
            return {"error": "アクティブなセッションがありません。"}

        if timer["state"] == "paused":
            return {"error": "既に一時停止中です。"}

        now = datetime.now(UTC)
        timer["state"] = "paused"
        timer["paused_at"] = now

        await self.repository.update_state(timer["session_id"], "paused", paused_at=now)
        return {"success": True}

    async def resume_session(self, user_id: int) -> dict:
        """セッション再開"""
        timer = self.active_timers.get(user_id)
        if not timer:
            return {"error": "アクティブなセッションがありません。"}

        if timer["state"] != "paused":
            return {"error": "一時停止中ではありません。"}

        now = datetime.now(UTC)
        paused_duration = (now - timer["paused_at"]).total_seconds()
        timer["accumulated_pause"] += paused_duration
        timer["state"] = "working"
        timer.pop("paused_at", None)

        await self.repository.update_state(timer["session_id"], "working")
        return {"success": True}

    async def stop_session(self, user_id: int) -> dict:
        """セッション停止"""
        timer = self.active_timers.pop(user_id, None)
        if not timer:
            return {"error": "アクティブなセッションがありません。"}

        now = datetime.now(UTC)
        total_seconds = int(
            (now - timer["started_at"]).total_seconds() - timer["accumulated_pause"]
        )

        await self.repository.update_state(
            timer["session_id"],
            "completed",
            ended_at=now,
            total_work_seconds=total_seconds,
        )

        return {
            "session_id": timer["session_id"],
            "topic": timer["topic"],
            "total_minutes": total_seconds // 60,
            "work_minutes": timer["work_minutes"],
        }

    def get_status(self, user_id: int) -> dict | None:
        """現在のタイマー状態を取得"""
        timer = self.active_timers.get(user_id)
        if not timer:
            return None

        now = datetime.now(UTC)
        phase_start = timer["phase_started_at"]
        pause_adj = timer["accumulated_pause"]

        if timer["state"] == "paused":
            pause_adj += (now - timer["paused_at"]).total_seconds()

        elapsed = (now - phase_start).total_seconds() - pause_adj

        if timer["state"] in ("working", "paused"):
            target = timer["work_minutes"] * 60
        else:
            target = timer["break_minutes"] * 60

        remaining = max(0, target - elapsed)
        progress = min(1.0, elapsed / target) if target > 0 else 1.0

        return {
            "state": timer["state"],
            "topic": timer["topic"],
            "remaining_seconds": int(remaining),
            "progress": progress,
            "work_minutes": timer["work_minutes"],
            "break_minutes": timer["break_minutes"],
        }

    def get_all_active_timers(self) -> dict[int, dict]:
        """全アクティブタイマーを返す（タスクループ用）"""
        return self.active_timers

    async def transition_to_break(self, user_id: int) -> dict | None:
        """作業→休憩に切り替え"""
        timer = self.active_timers.get(user_id)
        if not timer or timer["state"] != "working":
            return None

        now = datetime.now(UTC)
        timer["state"] = "break"
        timer["phase_started_at"] = now
        timer["accumulated_pause"] = 0

        await self.repository.update_state(timer["session_id"], "break")
        return {"break_minutes": timer["break_minutes"], "topic": timer["topic"]}

    async def complete_session(self, user_id: int) -> dict | None:
        """休憩終了→セッション完了"""
        timer = self.active_timers.pop(user_id, None)
        if not timer:
            return None

        now = datetime.now(UTC)
        total_seconds = int(
            (now - timer["started_at"]).total_seconds() - timer["accumulated_pause"]
        )

        await self.repository.update_state(
            timer["session_id"],
            "completed",
            ended_at=now,
            total_work_seconds=total_seconds,
        )

        return {
            "session_id": timer["session_id"],
            "topic": timer["topic"],
            "work_minutes": timer["work_minutes"],
            "total_minutes": total_seconds // 60,
            "channel_id": timer["channel_id"],
        }
