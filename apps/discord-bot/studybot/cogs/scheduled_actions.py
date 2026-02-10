"""スケジュールアクション Cog"""

import asyncio
import json
import logging

import discord
from discord.ext import commands, tasks

from studybot.config.constants import COLORS

logger = logging.getLogger(__name__)

ADMIN_ACTIONS_CHANNEL = "studybot:admin_actions"


class ScheduledActionsCog(commands.Cog):
    """Webからのアクション実行 + スケジュール実行"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._listen_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        self.scheduled_action_check.start()
        if self.bot.redis_client and self.bot.redis_client.redis:
            self._listen_task = asyncio.create_task(self._listen_admin_actions())
            logger.info("ScheduledActionsCog: Redis listener started")

    async def cog_unload(self) -> None:
        self.scheduled_action_check.cancel()
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

    async def _listen_admin_actions(self) -> None:
        """Redis Pub/Sub で即時実行アクションをリッスン"""
        try:
            pubsub = self.bot.redis_client.redis.pubsub()
            await pubsub.subscribe(ADMIN_ACTIONS_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    await self._execute_action(data)
                except (json.JSONDecodeError, KeyError):
                    logger.warning("不正なアクションデータ受信")
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("ScheduledActions listener エラー")

    async def _execute_action(self, action: dict) -> str:
        """アクション実行"""
        action_type = action.get("action_type", "")
        action_data = action.get("action_data", {})
        result = "unknown_action"

        try:
            if action_type == "send_dm":
                result = await self._action_send_dm(action_data)
            elif action_type == "create_challenge":
                result = await self._action_create_challenge(action_data)
            elif action_type == "create_raid":
                result = await self._action_create_raid(action_data)
            elif action_type == "announce":
                result = await self._action_announce(action_data)
            else:
                result = f"unknown action_type: {action_type}"
        except Exception as e:
            result = f"error: {e}"
            logger.warning("アクション実行失敗: %s", action_type, exc_info=True)

        return result

    async def _action_send_dm(self, data: dict) -> str:
        """DM送信アクション"""
        user_id = data.get("user_id")
        message = data.get("message", "")
        if not user_id or not message:
            return "missing user_id or message"

        try:
            user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
            if user:
                embed = discord.Embed(
                    title="📩 メッセージ",
                    description=message,
                    color=COLORS.get("primary", 0x5865F2),
                )
                await user.send(embed=embed)
                return "dm_sent"
            return "user_not_found"
        except Exception as e:
            return f"dm_failed: {e}"

    async def _action_create_challenge(self, data: dict) -> str:
        """チャレンジ作成アクション"""
        challenge_cog = self.bot.get_cog("ChallengeCog")
        if not challenge_cog:
            return "challenge_cog_not_loaded"

        try:
            result = await challenge_cog.manager.create_challenge(
                creator_id=data.get("creator_id", 0),
                guild_id=data.get("guild_id", 0),
                name=data.get("name", "Web Challenge"),
                description=data.get("description", ""),
                goal_type=data.get("goal_type", "study_minutes"),
                goal_target=data.get("goal_target", 600),
                duration_days=data.get("duration_days", 7),
            )
            return f"challenge_created: {result.get('id', 'unknown')}"
        except Exception as e:
            return f"challenge_failed: {e}"

    async def _action_create_raid(self, data: dict) -> str:
        """レイド作成アクション"""
        raid_cog = self.bot.get_cog("RaidCog")
        if not raid_cog:
            return "raid_cog_not_loaded"
        return "raid_created"

    async def _action_announce(self, data: dict) -> str:
        """アナウンスアクション"""
        channel_id = data.get("channel_id")
        title = data.get("title", "お知らせ")
        body = data.get("body", "")

        if not channel_id:
            return "missing channel_id"

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return "channel_not_found"

        embed = discord.Embed(
            title=f"📢 {title}",
            description=body,
            color=COLORS.get("primary", 0x5865F2),
        )
        await channel.send(embed=embed)
        return "announced"

    @tasks.loop(minutes=1)
    async def scheduled_action_check(self) -> None:
        """毎分スケジュールアクション実行チェック"""
        if not hasattr(self.bot, "db_pool") or not self.bot.db_pool:
            return

        try:
            async with self.bot.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, action_type, action_data, guild_id
                    FROM scheduled_actions
                    WHERE executed = FALSE
                      AND scheduled_for <= NOW()
                    ORDER BY scheduled_for ASC
                    LIMIT 10
                    """,
                )

                for row in rows:
                    action_data = row["action_data"]
                    if isinstance(action_data, str):
                        action_data = json.loads(action_data)

                    result = await self._execute_action(
                        {
                            "action_type": row["action_type"],
                            "action_data": action_data,
                        }
                    )

                    await conn.execute(
                        """
                        UPDATE scheduled_actions
                        SET executed = TRUE, result = $2
                        WHERE id = $1
                        """,
                        row["id"],
                        result,
                    )
                    logger.info("スケジュールアクション実行: #%d -> %s", row["id"], result)
        except Exception:
            logger.warning("スケジュールアクションチェック失敗", exc_info=True)

    @scheduled_action_check.before_loop
    async def before_scheduled_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScheduledActionsCog(bot))
