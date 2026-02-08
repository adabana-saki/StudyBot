"""スタディレイド Cog"""

import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COIN_REWARDS, RAID_DEFAULTS, XP_REWARDS
from studybot.managers.raid_manager import RaidManager
from studybot.utils.embed_helper import error_embed, raid_embed, success_embed

logger = logging.getLogger(__name__)


def _format_time(seconds: int) -> str:
    """秒を mm:ss に変換"""
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


class RaidJoinView(discord.ui.View):
    """レイド参加/離脱ボタン"""

    def __init__(self, cog: "RaidCog", raid_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.raid_id = raid_id

    @discord.ui.button(label="⚔️ 参加", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = await self.cog.manager.join_raid(
            self.raid_id, interaction.user.id, interaction.user.display_name
        )

        if "error" in result:
            await interaction.response.send_message(result["error"], ephemeral=True)
        else:
            await interaction.response.send_message(
                f"⚔️ {interaction.user.display_name} がレイドに参加しました！ "
                f"({result['participant_count']}/{result['raid']['max_participants']})",
            )

            # イベント発行: レイド参加
            bot = interaction.client
            if hasattr(bot, "event_publisher") and bot.event_publisher:
                try:
                    await bot.event_publisher.emit_raid_join(
                        user_id=interaction.user.id,
                        guild_id=getattr(interaction, "guild_id", 0) or 0,
                        username=interaction.user.display_name,
                        raid_topic=result.get("raid", {}).get("topic", ""),
                    )
                except Exception:
                    logger.warning("イベント発行失敗", exc_info=True)

    @discord.ui.button(label="🚪 離脱", style=discord.ButtonStyle.secondary)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = await self.cog.manager.leave_raid(self.raid_id, interaction.user.id)

        if "error" in result:
            await interaction.response.send_message(result["error"], ephemeral=True)
        else:
            await interaction.response.send_message(
                f"🚪 {interaction.user.display_name} がレイドから離脱しました。",
                ephemeral=True,
            )

    @discord.ui.button(label="🚀 開始", style=discord.ButtonStyle.danger)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 作成者のみ開始可能
        raid = await self.cog.manager.repository.get_raid(self.raid_id)
        if not raid or raid["creator_id"] != interaction.user.id:
            await interaction.response.send_message(
                "レイド作成者のみ開始できます。", ephemeral=True
            )
            return

        result = await self.cog.manager.start_raid(self.raid_id)
        if "error" in result:
            await interaction.response.send_message(result["error"], ephemeral=True)
            return

        participant_names = [p["username"] for p in result["participants"]]
        embed = raid_embed(
            "レイド開始！",
            f"**{raid['topic']}** ({raid['duration_minutes']}分間)\n\n"
            f"👥 参加者: {', '.join(participant_names)}\n\n"
            f"全員で集中して学習しましょう！💪",
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


class RaidCog(commands.Cog):
    """スタディレイド機能"""

    def __init__(self, bot: commands.Bot, manager: RaidManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.raid_check.start()

    async def cog_unload(self) -> None:
        self.raid_check.cancel()

    raid_group = app_commands.Group(name="raid", description="スタディレイド")

    @raid_group.command(name="create", description="スタディレイドを作成")
    @app_commands.describe(
        topic="レイドのトピック",
        duration="学習時間（分）",
        max_participants="最大参加人数",
    )
    async def raid_create(
        self,
        interaction: discord.Interaction,
        topic: str,
        duration: int,
        max_participants: int = RAID_DEFAULTS["max_participants"],
    ):
        await interaction.response.defer()

        result = await self.manager.create_raid(
            creator_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            topic=topic,
            duration=duration,
            max_participants=max_participants,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("レイド作成失敗", result["error"]))
            return

        embed = raid_embed(
            "スタディレイド募集！",
            f"**{topic}**\n\n"
            f"⏱️ 学習時間: {duration}分\n"
            f"👥 参加枠: 1/{max_participants}\n"
            f"🎯 XP {RAID_DEFAULTS['xp_multiplier']}倍ボーナス！\n\n"
            f"下のボタンから参加できます。\n"
            f"作成者が「開始」を押すとレイドが始まります。",
        )
        embed.set_footer(text=f"レイドID: {result['id']} | 作成者: {interaction.user.display_name}")

        view = RaidJoinView(self, result["id"])
        await interaction.followup.send(embed=embed, view=view)

    @raid_group.command(name="join", description="レイドに参加")
    @app_commands.describe(raid_id="レイドID")
    async def raid_join(self, interaction: discord.Interaction, raid_id: int):
        result = await self.manager.join_raid(
            raid_id, interaction.user.id, interaction.user.display_name
        )

        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("参加失敗", result["error"]), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success_embed(
                "レイド参加！",
                f"レイド #{raid_id} に参加しました！ "
                f"({result['participant_count']}/{result['raid']['max_participants']})",
            )
        )

        # イベント発行: レイド参加
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_raid_join(
                    user_id=interaction.user.id,
                    guild_id=getattr(interaction, "guild_id", 0) or 0,
                    username=interaction.user.display_name,
                    raid_topic=result.get("raid", {}).get("topic", ""),
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

    @raid_group.command(name="leave", description="レイドから離脱")
    @app_commands.describe(raid_id="レイドID")
    async def raid_leave(self, interaction: discord.Interaction, raid_id: int):
        result = await self.manager.leave_raid(raid_id, interaction.user.id)

        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("離脱失敗", result["error"]), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success_embed("レイド離脱", "レイドから離脱しました。"),
            ephemeral=True,
        )

    @raid_group.command(name="status", description="アクティブなレイド一覧を表示")
    async def raid_status(self, interaction: discord.Interaction):
        await interaction.response.defer()

        raids = await self.manager.get_active_raids(interaction.guild_id)

        if not raids:
            await interaction.followup.send(
                embed=raid_embed("スタディレイド", "アクティブなレイドはありません。")
            )
            return

        lines = []
        state_labels = {"recruiting": "📢 募集中", "active": "🔥 進行中"}

        for raid in raids:
            state = state_labels.get(raid["state"], raid["state"])
            lines.append(
                f"**#{raid['id']}** {state}\n"
                f"　📚 {raid['topic']} ({raid['duration_minutes']}分)\n"
                f"　👥 {raid['participant_count']}/{raid['max_participants']} | "
                f"作成者: {raid['creator_name']}"
            )

        embed = raid_embed("アクティブなレイド", "\n\n".join(lines))
        embed.set_footer(text=f"{len(raids)}件のレイド")
        await interaction.followup.send(embed=embed)

    @tasks.loop(seconds=30)
    async def raid_check(self):
        """30秒ごとにアクティブレイドの完了をチェック"""
        try:
            await self._raid_check_impl()
        except Exception:
            logger.error("レイドチェック中にエラー", exc_info=True)

    async def _raid_check_impl(self):
        to_complete = []
        now = datetime.now(UTC)

        for raid_id, timer in self.manager.get_all_active_timers().items():
            elapsed = (now - timer["started_at"]).total_seconds()
            if elapsed >= timer["duration_minutes"] * 60:
                to_complete.append(raid_id)

        for raid_id in to_complete:
            timer = self.manager.active_raids.get(raid_id)
            if not timer:
                continue

            channel_id = timer["channel_id"]
            result = await self.manager.complete_raid(raid_id)

            if "error" in result:
                continue

            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            # 完了通知
            participants = result["participants"]
            participant_mentions = [f"<@{p['user_id']}>" for p in participants]

            embed = raid_embed(
                "レイド完了！🎉",
                f"**{result['raid']['topic']}** のスタディレイドが完了しました！\n\n"
                f"👥 参加者: {', '.join(participant_mentions)}\n"
                f"⏱️ 学習時間: {result['raid']['duration_minutes']}分",
            )
            await channel.send(" ".join(participant_mentions), embed=embed)

            # イベント発行: レイド完了（各参加者に対して）
            if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
                raid_topic = result.get("raid", {}).get("topic", "")
                participant_count = len(participants)
                for p in participants:
                    try:
                        await self.bot.event_publisher.emit_raid_complete(
                            user_id=p["user_id"],
                            guild_id=timer.get("guild_id", 0) or 0,
                            username=p.get("username", ""),
                            raid_topic=raid_topic,
                            participants=participant_count,
                        )
                    except Exception:
                        logger.warning("イベント発行失敗", exc_info=True)

            # XP・コイン付与
            gamification = self.bot.get_cog("GamificationCog")
            shop_cog = self.bot.get_cog("ShopCog")
            achievement_cog = self.bot.get_cog("AchievementCog")

            for p in participants:
                user_id = p["user_id"]

                # XP付与（レイドボーナス倍率）
                if gamification:
                    try:
                        await gamification.award_raid_xp(
                            user_id, XP_REWARDS["pomodoro_complete"], channel
                        )
                    except Exception:
                        logger.warning(f"レイドXP付与に失敗 (user={user_id})", exc_info=True)

                # コイン付与
                if shop_cog:
                    try:
                        is_creator = user_id == result["raid"]["creator_id"]
                        coin_amount = (
                            COIN_REWARDS["raid_host"]
                            if is_creator
                            else COIN_REWARDS["raid_complete"]
                        )
                        await shop_cog.award_coins(user_id, "", coin_amount, "レイド完了")
                    except Exception:
                        logger.warning(f"レイドコイン付与に失敗 (user={user_id})", exc_info=True)

                # 実績チェック
                if achievement_cog:
                    try:
                        await achievement_cog.check_achievement(user_id, "first_raid", 1, channel)
                    except Exception:
                        logger.warning(f"レイド実績チェックに失敗 (user={user_id})", exc_info=True)

    @raid_check.before_loop
    async def before_raid_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = RaidManager(db_pool)
    await bot.add_cog(RaidCog(bot, manager))
