"""スタディルーム マネージャー"""

import asyncio
import logging
from datetime import UTC, datetime

from studybot.repositories.room_repository import RoomRepository

logger = logging.getLogger(__name__)


class RoomManager:
    """スタディルームのビジネスロジック"""

    def __init__(self, db_pool, event_publisher=None) -> None:
        self.db_pool = db_pool
        self.room_repo = RoomRepository(db_pool)
        self.event_publisher = event_publisher
        self._lock = asyncio.Lock()

    async def create_room(
        self,
        guild_id: int,
        name: str,
        theme: str = "general",
        vc_channel_id: int | None = None,
        goal_minutes: int = 0,
        created_by: int | None = None,
    ) -> dict:
        """ルーム作成"""
        valid_themes = {"general", "math", "english", "science", "programming", "art", "music"}
        if theme not in valid_themes:
            return {"error": f"無効なテーマ: {theme}"}

        if len(name) > 100:
            return {"error": "ルーム名は100文字以内で指定してください"}

        room = await self.room_repo.create_room(
            guild_id=guild_id,
            name=name,
            theme=theme,
            vc_channel_id=vc_channel_id,
            collective_goal_minutes=goal_minutes,
            created_by=created_by,
        )
        return room

    async def join_room(
        self,
        room_id: int,
        user_id: int,
        platform: str = "discord",
        topic: str = "",
    ) -> dict:
        """ルーム参加"""
        room = await self.room_repo.get_room(room_id)
        if not room:
            return {"error": "ルームが見つかりません"}

        if room["member_count"] >= room["max_occupants"]:
            return {"error": "ルームが満員です"}

        # Leave any existing room first
        current = await self.room_repo.get_user_room(user_id)
        if current:
            await self.leave_room(current["room_id"], user_id)

        success = await self.room_repo.join_room(room_id, user_id, platform, topic)
        if not success:
            return {"error": "参加に失敗しました"}

        # Emit event
        if self.event_publisher:
            try:
                await self.event_publisher._emit(
                    "room_join",
                    {
                        "room_id": room_id,
                        "user_id": user_id,
                        "platform": platform,
                        "topic": topic,
                        "guild_id": room["guild_id"],
                    },
                )
            except Exception:
                logger.debug("room_joinイベント発行失敗", exc_info=True)

        return {"status": "joined", "room_id": room_id}

    async def leave_room(self, room_id: int, user_id: int) -> dict:
        """ルーム退出"""
        member = await self.room_repo.leave_room(room_id, user_id)
        if not member:
            return {"error": "ルームに参加していません"}

        # Record history
        joined_at = member.get("joined_at", datetime.now(UTC))
        now = datetime.now(UTC)
        if joined_at.tzinfo is None:
            from datetime import timezone
            joined_at = joined_at.replace(tzinfo=timezone.utc)
        duration = int((now - joined_at).total_seconds() / 60)

        await self.room_repo.record_room_history(
            room_id, user_id, member.get("platform", "discord"),
            joined_at, duration,
        )

        # Update collective progress
        if duration > 0:
            progress = await self.room_repo.update_collective_progress(
                room_id, duration
            )
            if progress and progress["collective_goal_minutes"] > 0:
                if progress["collective_progress_minutes"] >= progress["collective_goal_minutes"]:
                    if self.event_publisher:
                        room = await self.room_repo.get_room(room_id)
                        try:
                            await self.event_publisher._emit(
                                "room_goal_reached",
                                {
                                    "room_id": room_id,
                                    "guild_id": room["guild_id"] if room else 0,
                                    "user_id": user_id,
                                },
                            )
                        except Exception:
                            logger.debug("room_goal_reachedイベント発行失敗", exc_info=True)

        # Emit leave event
        if self.event_publisher:
            room = await self.room_repo.get_room(room_id)
            try:
                await self.event_publisher._emit(
                    "room_leave",
                    {
                        "room_id": room_id,
                        "user_id": user_id,
                        "guild_id": room["guild_id"] if room else 0,
                        "duration_minutes": duration,
                    },
                )
            except Exception:
                logger.debug("room_leaveイベント発行失敗", exc_info=True)

        return {"status": "left", "duration_minutes": duration}

    async def get_campus(self, guild_id: int) -> list[dict]:
        """全ルーム取得"""
        return await self.room_repo.get_guild_rooms(guild_id)

    async def sync_vc_room(
        self, vc_channel_id: int, member_ids: list[int]
    ) -> None:
        """Discord VCメンバーとルームを同期"""
        room = await self.room_repo.get_room_by_vc_channel(vc_channel_id)
        if not room:
            return

        current_members = await self.room_repo.get_room_members(room["id"])
        current_ids = {m["user_id"] for m in current_members if m["platform"] == "discord"}

        new_ids = set(member_ids)

        # Join new members
        for uid in new_ids - current_ids:
            await self.room_repo.join_room(room["id"], uid, "discord")

        # Remove departed members (discord only)
        for uid in current_ids - new_ids:
            await self.leave_room(room["id"], uid)
