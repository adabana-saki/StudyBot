"""スタディレイド ビジネスロジック"""

import asyncio
import logging
from datetime import UTC, datetime

from studybot.config.constants import RAID_DEFAULTS
from studybot.repositories.raid_repository import RaidRepository

logger = logging.getLogger(__name__)


class RaidManager:
    """スタディレイドの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = RaidRepository(db_pool)
        # メモリ内レイド状態 (raid_id -> timer info)
        self.active_raids: dict[int, dict] = {}
        self._lock = asyncio.Lock()

    async def create_raid(
        self,
        creator_id: int,
        username: str,
        guild_id: int,
        channel_id: int,
        topic: str,
        duration: int,
        max_participants: int = RAID_DEFAULTS["max_participants"],
    ) -> dict:
        """レイドを作成"""
        await self.repository.ensure_user(creator_id, username)

        # バリデーション
        if duration < RAID_DEFAULTS["min_duration"]:
            return {"error": f"最低{RAID_DEFAULTS['min_duration']}分必要です"}
        if duration > RAID_DEFAULTS["max_duration"]:
            return {"error": f"最大{RAID_DEFAULTS['max_duration']}分までです"}

        raid = await self.repository.create_raid(
            creator_id, guild_id, channel_id, topic, duration, max_participants
        )

        # 作成者を自動参加
        await self.repository.add_participant(raid["id"], creator_id)

        return raid

    async def join_raid(self, raid_id: int, user_id: int, username: str) -> dict:
        """レイドに参加"""
        await self.repository.ensure_user(user_id, username)

        raid = await self.repository.get_raid(raid_id)
        if not raid:
            return {"error": "レイドが見つかりません"}

        if raid["state"] != "recruiting":
            return {"error": "このレイドは参加を募集していません"}

        # 人数チェック
        count = await self.repository.get_participant_count(raid_id)
        if count >= raid["max_participants"]:
            return {"error": "参加者が上限に達しています"}

        added = await self.repository.add_participant(raid_id, user_id)
        if not added:
            return {"error": "既に参加しています"}

        participant_count = await self.repository.get_participant_count(raid_id)
        return {
            "raid": raid,
            "participant_count": participant_count,
        }

    async def leave_raid(self, raid_id: int, user_id: int) -> dict:
        """レイドから離脱"""
        raid = await self.repository.get_raid(raid_id)
        if not raid:
            return {"error": "レイドが見つかりません"}

        if raid["state"] not in ("recruiting", "active"):
            return {"error": "このレイドからは離脱できません"}

        if raid["creator_id"] == user_id:
            return {"error": "レイド作成者は離脱できません"}

        removed = await self.repository.remove_participant(raid_id, user_id)
        if not removed:
            return {"error": "参加していません"}

        return {"success": True}

    async def start_raid(self, raid_id: int) -> dict:
        """レイドを開始"""
        async with self._lock:
            raid = await self.repository.get_raid(raid_id)
            if not raid:
                return {"error": "レイドが見つかりません"}

            if raid["state"] != "recruiting":
                return {"error": "このレイドは開始できません"}

            await self.repository.start_raid(raid_id)

            # メモリ内タイマー設定
            now = datetime.now(UTC)
            self.active_raids[raid_id] = {
                "raid_id": raid_id,
                "started_at": now,
                "duration_minutes": raid["duration_minutes"],
                "channel_id": raid["channel_id"],
                "guild_id": raid["guild_id"],
                "topic": raid["topic"],
                "creator_id": raid["creator_id"],
            }

            participants = await self.repository.get_participants(raid_id)
            return {
                "raid": raid,
                "participants": participants,
            }

    async def complete_raid(self, raid_id: int) -> dict:
        """レイドを完了"""
        async with self._lock:
            raid = await self.repository.get_raid(raid_id)
            if not raid:
                return {"error": "レイドが見つかりません"}

            # 全参加者を完了にマーク
            participants = await self.repository.get_participants(raid_id)
            for p in participants:
                await self.repository.mark_participant_completed(raid_id, p["user_id"])

            await self.repository.complete_raid(raid_id)

            # メモリからタイマー削除
            self.active_raids.pop(raid_id, None)

            return {
                "raid": raid,
                "participants": participants,
            }

    async def get_active_raids(self, guild_id: int) -> list[dict]:
        """ギルドのアクティブなレイド一覧を取得"""
        return await self.repository.get_active_raids_with_counts(guild_id)

    async def get_raid_status(self, raid_id: int) -> dict | None:
        """レイドの詳細ステータスを取得"""
        raid = await self.repository.get_raid(raid_id)
        if not raid:
            return None

        participants = await self.repository.get_participants(raid_id)

        # 残り時間計算
        remaining_seconds = None
        timer = self.active_raids.get(raid_id)
        if timer and raid["state"] == "active":
            elapsed = (datetime.now(UTC) - timer["started_at"]).total_seconds()
            remaining_seconds = max(0, int(timer["duration_minutes"] * 60 - elapsed))

        return {
            "raid": raid,
            "participants": participants,
            "remaining_seconds": remaining_seconds,
        }

    def get_all_active_timers(self) -> dict[int, dict]:
        """全アクティブレイドタイマーを返す（タスクループ用）"""
        return self.active_raids
