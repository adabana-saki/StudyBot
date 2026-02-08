"""リアルタイムイベント発行サービス"""

import logging
from datetime import UTC, datetime

from studybot.services.redis_client import RedisClient

logger = logging.getLogger(__name__)

EVENTS_CHANNEL = "studybot:events"
SESSIONS_CHANNEL = "studybot:sessions"


class EventPublisher:
    """型付きイベント発行 + アクティビティDB永続化"""

    def __init__(self, redis_client: RedisClient, db_pool=None) -> None:
        self.redis = redis_client
        self.db_pool = db_pool
        self._activity_repo = None

    @property
    def activity_repo(self):
        if self._activity_repo is None and self.db_pool:
            from studybot.repositories.activity_repository import ActivityRepository

            self._activity_repo = ActivityRepository(self.db_pool)
        return self._activity_repo

    async def _emit(self, event_type: str, data: dict) -> None:
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self.redis.publish(EVENTS_CHANNEL, payload)

        # activity_events テーブルに永続化
        if self.activity_repo:
            try:
                await self.activity_repo.save_event(
                    user_id=data.get("user_id", 0),
                    guild_id=data.get("guild_id", 0),
                    event_type=event_type,
                    event_data=data,
                )
            except Exception:
                logger.warning(
                    "アクティビティ永続化失敗: %s", event_type, exc_info=True
                )

    async def emit_study_start(
        self, *, user_id: int, guild_id: int, topic: str, username: str
    ) -> None:
        await self._emit(
            "study_start",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "topic": topic,
                "username": username,
            },
        )

    async def emit_study_end(
        self,
        *,
        user_id: int,
        guild_id: int,
        topic: str,
        username: str,
        duration_minutes: int,
    ) -> None:
        await self._emit(
            "study_end",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "topic": topic,
                "username": username,
                "duration_minutes": duration_minutes,
            },
        )

    async def emit_pomodoro_complete(
        self,
        *,
        user_id: int,
        guild_id: int,
        topic: str,
        username: str,
        work_minutes: int,
    ) -> None:
        await self._emit(
            "pomodoro_complete",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "topic": topic,
                "username": username,
                "work_minutes": work_minutes,
            },
        )

    async def emit_study_log(
        self,
        *,
        user_id: int,
        guild_id: int,
        topic: str,
        username: str,
        duration_minutes: int,
    ) -> None:
        await self._emit(
            "study_log",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "topic": topic,
                "username": username,
                "duration_minutes": duration_minutes,
            },
        )

    async def emit_xp_gain(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        amount: int,
        reason: str,
    ) -> None:
        await self._emit(
            "xp_gain",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "amount": amount,
                "reason": reason,
            },
        )

    async def emit_level_up(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        new_level: int,
    ) -> None:
        await self._emit(
            "level_up",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "new_level": new_level,
            },
        )

    async def emit_achievement_unlock(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        achievement_name: str,
        achievement_emoji: str,
    ) -> None:
        await self._emit(
            "achievement_unlock",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "achievement_name": achievement_name,
                "achievement_emoji": achievement_emoji,
            },
        )

    async def emit_todo_complete(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        title: str,
    ) -> None:
        await self._emit(
            "todo_complete",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "title": title,
            },
        )

    async def emit_focus_start(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        duration_minutes: int,
    ) -> None:
        await self._emit(
            "focus_start",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "duration_minutes": duration_minutes,
            },
        )

    async def emit_focus_end(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        duration_minutes: int,
    ) -> None:
        await self._emit(
            "focus_end",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "duration_minutes": duration_minutes,
            },
        )

    async def emit_lock_start(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        duration_minutes: int,
    ) -> None:
        await self._emit(
            "lock_start",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "duration_minutes": duration_minutes,
            },
        )

    async def emit_lock_end(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
    ) -> None:
        await self._emit(
            "lock_end",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
            },
        )

    async def emit_raid_join(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        raid_topic: str,
    ) -> None:
        await self._emit(
            "raid_join",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "raid_topic": raid_topic,
            },
        )

    async def emit_raid_complete(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        raid_topic: str,
        participants: int,
    ) -> None:
        await self._emit(
            "raid_complete",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "raid_topic": raid_topic,
                "participants": participants,
            },
        )

    async def emit_flashcard_review(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        deck_name: str,
        cards_reviewed: int,
    ) -> None:
        await self._emit(
            "flashcard_review",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "deck_name": deck_name,
                "cards_reviewed": cards_reviewed,
            },
        )

    async def emit_buddy_match(
        self,
        *,
        user_a: int,
        user_b: int,
        guild_id: int,
        subject: str,
        score: float,
    ) -> None:
        await self._emit(
            "buddy_match",
            {
                "user_a": user_a,
                "user_b": user_b,
                "guild_id": guild_id,
                "subject": subject,
                "compatibility_score": score,
            },
        )

    async def emit_challenge_join(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        challenge_name: str,
    ) -> None:
        await self._emit(
            "challenge_join",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "challenge_name": challenge_name,
            },
        )

    async def emit_challenge_checkin(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        challenge_name: str,
        progress: int,
    ) -> None:
        await self._emit(
            "challenge_checkin",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "challenge_name": challenge_name,
                "progress": progress,
            },
        )

    async def emit_session_sync(
        self,
        *,
        user_id: int,
        session_type: str,
        source: str,
        action: str,
        topic: str = "",
    ) -> None:
        payload = {
            "user_id": user_id,
            "session_type": session_type,
            "source": source,
            "action": action,
            "topic": topic,
        }
        await self.redis.publish(
            SESSIONS_CHANNEL,
            {
                "type": "session_sync",
                "data": payload,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def emit_insights_ready(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        insights_count: int,
    ) -> None:
        await self._emit(
            "insights_ready",
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "username": username,
                "insights_count": insights_count,
            },
        )
