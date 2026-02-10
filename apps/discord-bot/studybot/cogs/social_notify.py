"""ソーシャル通知 Cog - タイムラインリアクション/コメントのDM通知"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.utils.embed_helper import info_embed

logger = logging.getLogger(__name__)

EVENTS_CHANNEL = "studybot:events"


class SocialNotifyCog(commands.Cog):
    """タイムラインリアクション/コメントのDM通知"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._notified_cache: dict[str, float] = {}  # event_id:user_id -> timestamp
        self._listen_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        if self.bot.redis_client and self.bot.redis_client.redis:
            self._listen_task = asyncio.create_task(self._listen_events())
            logger.info("SocialNotifyCog: Redis listener started")

    async def cog_unload(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

    async def _listen_events(self) -> None:
        """Redis Pub/Sub でソーシャルイベントをリッスン"""
        try:
            pubsub = self.bot.redis_client.redis.pubsub()
            await pubsub.subscribe(EVENTS_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    event_type = data.get("type", "")
                    if event_type in ("social_reaction", "social_comment"):
                        await self._handle_social_event(data)
                except (json.JSONDecodeError, KeyError):
                    logger.warning("不正なソーシャルイベント受信")
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("SocialNotifyCog listener エラー")

    async def _handle_social_event(self, data: dict) -> None:
        """ソーシャルイベントのDM通知処理"""
        event_data = data.get("data", {})
        target_user_id = event_data.get("target_user_id")
        actor_username = event_data.get("actor_username", "someone")
        event_id = event_data.get("event_id", 0)
        event_type = data.get("type", "")

        if not target_user_id:
            return

        # Don't notify yourself
        actor_id = event_data.get("actor_user_id", 0)
        if actor_id == target_user_id:
            return

        # Rate limit: 1 notification per event_id per hour
        cache_key = f"{event_id}:{target_user_id}"
        now = datetime.now(UTC).timestamp()
        last_notified = self._notified_cache.get(cache_key, 0)
        if now - last_notified < 3600:
            return
        self._notified_cache[cache_key] = now

        # Clean old cache entries (older than 2 hours)
        cutoff = now - 7200
        self._notified_cache = {k: v for k, v in self._notified_cache.items() if v > cutoff}

        # Send DM
        try:
            user = self.bot.get_user(target_user_id) or await self.bot.fetch_user(target_user_id)
            if not user:
                return

            if event_type == "social_reaction":
                reaction_type = event_data.get("reaction_type", "applaud")
                emoji_map = {"applaud": "👏", "fire": "🔥", "heart": "❤️", "study_on": "📚"}
                emoji = emoji_map.get(reaction_type, "👏")
                embed = info_embed(
                    f"{emoji} リアクション通知",
                    f"**{actor_username}** があなたのアクティビティに{emoji}しました！",
                )
            else:
                body_preview = event_data.get("body", "")[:100]
                embed = info_embed(
                    "💬 コメント通知",
                    f"**{actor_username}** があなたのアクティビティに"
                    f"コメントしました：\n> {body_preview}",
                )

            embed.color = COLORS.get("primary", 0x5865F2)
            await user.send(embed=embed)
        except Exception:
            logger.debug("ソーシャルDM通知失敗 (user=%d)", target_user_id, exc_info=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SocialNotifyCog(bot))
