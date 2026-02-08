"""ポモドーロタイマー ビジネスロジック"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from studybot.repositories.pomodoro_repository import PomodoroRepository

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "pomodoro"
REDIS_TTL_SECONDS = 4 * 60 * 60  # 4時間


class PomodoroManager:
    """ポモドーロタイマーの管理"""

    def __init__(self, db_pool, redis_client=None) -> None:
        self.repository = PomodoroRepository(db_pool)
        self.redis_client = redis_client
        # メモリ内タイマー状態 (user_id -> session_info)
        self.active_timers: dict[int, dict] = {}
        self._lock = asyncio.Lock()

    def _redis_key(self, user_id: int) -> str:
        """Redisキーを生成"""
        return f"{REDIS_KEY_PREFIX}:{user_id}"

    def _serialize_timer(self, timer: dict) -> str:
        """タイマー状態をJSON文字列にシリアライズ"""
        data = dict(timer)
        # datetimeオブジェクトをISO形式に変換
        for key in ("started_at", "phase_started_at", "paused_at"):
            if key in data and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return json.dumps(data)

    @staticmethod
    def _deserialize_timer(raw: str) -> dict:
        """JSON文字列をタイマー状態に復元"""
        data = json.loads(raw)
        for key in ("started_at", "phase_started_at", "paused_at"):
            if key in data and data[key] is not None:
                data[key] = datetime.fromisoformat(data[key])
        return data

    async def _save_to_redis(self, user_id: int) -> None:
        """タイマー状態をRedisに保存"""
        if not self.redis_client:
            return
        timer = self.active_timers.get(user_id)
        if not timer:
            return
        try:
            await self.redis_client.set(
                self._redis_key(user_id),
                self._serialize_timer(timer),
                ex=REDIS_TTL_SECONDS,
            )
        except Exception:
            logger.warning("Redis保存失敗 (user=%s)", user_id, exc_info=True)

    async def _delete_from_redis(self, user_id: int) -> None:
        """Redisからタイマー状態を削除"""
        if not self.redis_client:
            return
        try:
            await self.redis_client.delete(self._redis_key(user_id))
        except Exception:
            logger.warning("Redis削除失敗 (user=%s)", user_id, exc_info=True)

    async def restore_sessions(self) -> int:
        """Redisから全ポモドーロセッションを復元する（起動時に呼び出す）

        Returns:
            復元したセッション数
        """
        if not self.redis_client:
            return 0

        restored = 0
        try:
            keys = await self.redis_client.keys(f"{REDIS_KEY_PREFIX}:*")
            for key in keys:
                try:
                    raw = await self.redis_client.get(key)
                    if not raw:
                        continue
                    timer = self._deserialize_timer(raw)
                    # キーからuser_idを抽出
                    user_id = int(key.split(":")[-1])
                    self.active_timers[user_id] = timer
                    restored += 1
                    logger.info("ポモドーロセッション復元: user=%s", user_id)
                except Exception:
                    logger.warning("セッション復元失敗: key=%s", key, exc_info=True)
        except Exception:
            logger.warning("Redisからのセッション復元に失敗", exc_info=True)

        if restored:
            logger.info("合計 %d 件のポモドーロセッションを復元しました", restored)
        return restored

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
        async with self._lock:
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

            await self._save_to_redis(user_id)

            return {
                "session_id": session_id,
                "topic": topic,
                "work_minutes": work_minutes,
                "break_minutes": break_minutes,
            }

    async def pause_session(self, user_id: int) -> dict:
        """セッション一時停止"""
        async with self._lock:
            timer = self.active_timers.get(user_id)
            if not timer:
                return {"error": "アクティブなセッションがありません。"}

            if timer["state"] == "paused":
                return {"error": "既に一時停止中です。"}

            now = datetime.now(UTC)
            timer["state"] = "paused"
            timer["paused_at"] = now

            await self.repository.update_state(timer["session_id"], "paused", paused_at=now)
            await self._save_to_redis(user_id)
            return {"success": True}

    async def resume_session(self, user_id: int) -> dict:
        """セッション再開"""
        async with self._lock:
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
            await self._save_to_redis(user_id)
            return {"success": True}

    async def stop_session(self, user_id: int) -> dict:
        """セッション停止"""
        async with self._lock:
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

            await self._delete_from_redis(user_id)

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
        async with self._lock:
            timer = self.active_timers.get(user_id)
            if not timer or timer["state"] != "working":
                return None

            now = datetime.now(UTC)
            timer["state"] = "break"
            timer["phase_started_at"] = now
            timer["accumulated_pause"] = 0

            await self.repository.update_state(timer["session_id"], "break")
            await self._save_to_redis(user_id)
            return {"break_minutes": timer["break_minutes"], "topic": timer["topic"]}

    async def complete_session(self, user_id: int) -> dict | None:
        """休憩終了→セッション完了"""
        async with self._lock:
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

            await self._delete_from_redis(user_id)

            return {
                "session_id": timer["session_id"],
                "topic": timer["topic"],
                "work_minutes": timer["work_minutes"],
                "total_minutes": total_seconds // 60,
                "channel_id": timer["channel_id"],
            }
