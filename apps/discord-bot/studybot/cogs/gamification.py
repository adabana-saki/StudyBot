"""ゲーミフィケーション（XP/レベル）Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS, XP_REWARDS
from studybot.managers.gamification_manager import GamificationManager
from studybot.utils.embed_helper import xp_embed

logger = logging.getLogger(__name__)


def _progress_bar(current: int, target: int, width: int = 15) -> str:
    """レベル進捗バー"""
    ratio = min(1.0, current / target) if target > 0 else 0
    filled = int(width * ratio)
    bar = "▓" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{target} XP"


class GamificationCog(commands.Cog):
    """XP & レベルシステム"""

    def __init__(self, bot: commands.Bot, manager: GamificationManager) -> None:
        self.bot = bot
        self.manager = manager

    @app_commands.command(name="profile", description="自分のプロフィールを表示")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer()

        await self.manager.ensure_user(interaction.user.id, interaction.user.display_name)
        profile = await self.manager.get_profile(interaction.user.id)

        if not profile:
            await interaction.followup.send("プロフィールが見つかりません。", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{profile['badge']} {interaction.user.display_name}",
            color=COLORS["xp"],
        )
        embed.add_field(name="レベル", value=f"Lv.{profile['level']}", inline=True)
        embed.add_field(name="総XP", value=f"{profile['xp']:,} XP", inline=True)
        embed.add_field(name="ランク", value=f"#{profile['rank']}", inline=True)
        embed.add_field(
            name="次のレベルまで",
            value=_progress_bar(profile["current_progress"], profile["next_level_xp"]),
            inline=False,
        )
        embed.add_field(
            name="連続学習",
            value=f"🔥 {profile['streak_days']}日",
            inline=True,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="xp", description="現在のXPとレベルを表示")
    async def xp_command(self, interaction: discord.Interaction):
        await self.manager.ensure_user(interaction.user.id, interaction.user.display_name)
        profile = await self.manager.get_profile(interaction.user.id)

        if not profile:
            await interaction.response.send_message("データが見つかりません。", ephemeral=True)
            return

        embed = xp_embed(
            f"⭐ Lv.{profile['level']} - {profile['xp']:,} XP",
            _progress_bar(profile["current_progress"], profile["next_level_xp"]),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def award_pomodoro_xp(self, user_id: int, channel: discord.abc.Messageable) -> None:
        """ポモドーロ完了時のXP付与（他Cogから呼び出し）"""
        amount = XP_REWARDS["pomodoro_complete"]
        result = await self.manager.add_xp(user_id, amount, "ポモドーロ完了")
        await self._send_xp_notification(user_id, channel, result)

        # 連続学習チェック
        streak = await self.manager.check_streak(user_id)
        if streak["bonus"]:
            bonus_result = await self.manager.add_xp(
                user_id, XP_REWARDS["streak_bonus"], "連続学習ボーナス"
            )
            await channel.send(
                embed=xp_embed(
                    f"🔥 連続{streak['streak']}日ボーナス！",
                    f"+{XP_REWARDS['streak_bonus']} XP",
                )
            )
            if bonus_result.get("leveled_up"):
                await self._send_levelup(user_id, channel, bonus_result)

    async def award_task_xp(
        self, user_id: int, priority: int, channel: discord.abc.Messageable
    ) -> None:
        """タスク完了時のXP付与（他Cogから呼び出し）"""
        reward_key = {1: "task_complete_high", 2: "task_complete_medium", 3: "task_complete_low"}
        amount = XP_REWARDS.get(reward_key.get(priority, "task_complete_low"), 10)
        result = await self.manager.add_xp(user_id, amount, "タスク完了")
        await self._send_xp_notification(user_id, channel, result)

    async def award_study_log_xp(self, user_id: int, channel: discord.abc.Messageable) -> None:
        """学習ログ記録時のXP付与"""
        amount = XP_REWARDS["study_log"]
        result = await self.manager.add_xp(user_id, amount, "学習ログ記録")
        await self._send_xp_notification(user_id, channel, result)

        streak = await self.manager.check_streak(user_id)
        if streak["bonus"]:
            await channel.send(
                embed=xp_embed(
                    f"🔥 連続{streak['streak']}日ボーナス！",
                    f"+{XP_REWARDS['streak_bonus']} XP",
                )
            )

    async def _send_xp_notification(
        self, user_id: int, channel: discord.abc.Messageable, result: dict
    ) -> None:
        """XP獲得通知を送信"""
        if "error" in result:
            return

        embed = xp_embed(
            f"+{result['xp_gained']} XP",
            f"合計: {result['total_xp']:,} XP | Lv.{result['new_level']}",
        )
        await channel.send(f"<@{user_id}>", embed=embed)

        if result.get("leveled_up"):
            await self._send_levelup(user_id, channel, result)

    async def _send_levelup(
        self, user_id: int, channel: discord.abc.Messageable, result: dict
    ) -> None:
        """レベルアップ通知"""
        milestone = result.get("milestone")
        badge = milestone["badge"] if milestone else "🎉"
        desc = f"**レベル {result['old_level']} → {result['new_level']}**"

        if milestone:
            desc += f"\n\n{milestone['badge']} **{milestone.get('role_name', '')}** の称号を獲得！"
            if milestone.get("description"):
                desc += f"\n_{milestone['description']}_"

        embed = discord.Embed(
            title=f"{badge} レベルアップ！",
            description=desc,
            color=COLORS["xp"],
        )
        await channel.send(f"<@{user_id}>", embed=embed)

        # スマホ通知
        nudge_cog = self.bot.get_cog("PhoneNudgeCog")
        if nudge_cog:
            await nudge_cog.send_nudge(
                user_id,
                "level_up",
                f"🎉 レベルアップ！ Lv.{result['new_level']} に到達しました！",
            )


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = GamificationManager(db_pool)
    await bot.add_cog(GamificationCog(bot, manager))
