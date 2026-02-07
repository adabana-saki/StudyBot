"""スマホ通知 Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.nudge_manager import NudgeManager
from studybot.utils.embed_helper import error_embed, success_embed

logger = logging.getLogger(__name__)


class PhoneNudgeCog(commands.Cog):
    """スマホ通知機能"""

    def __init__(self, bot: commands.Bot, manager: NudgeManager) -> None:
        self.bot = bot
        self.manager = manager

    nudge_group = app_commands.Group(name="nudge", description="スマホ通知設定")

    @nudge_group.command(name="setup", description="Webhook URLを設定")
    @app_commands.describe(webhook_url="通知先のWebhook URL")
    async def nudge_setup(self, interaction: discord.Interaction, webhook_url: str):
        result = await self.manager.setup_webhook(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            webhook_url=webhook_url,
        )

        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("設定エラー", result["error"]),
                ephemeral=True,
            )
            return

        embed = success_embed(
            "通知設定完了",
            "Webhook URLが設定されました。\n学習開始やレベルアップ時に通知が届きます。",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nudge_group.command(name="toggle", description="通知のON/OFF切り替え")
    @app_commands.describe(enabled="通知を有効にするか")
    async def nudge_toggle(self, interaction: discord.Interaction, enabled: bool):
        success = await self.manager.toggle(interaction.user.id, enabled)
        if not success:
            await interaction.response.send_message(
                embed=error_embed("エラー", "まず /nudge setup で設定してください。"),
                ephemeral=True,
            )
            return

        status = "有効" if enabled else "無効"
        await interaction.response.send_message(
            embed=success_embed("通知設定", f"通知を**{status}**にしました。"),
            ephemeral=True,
        )

    @nudge_group.command(name="test", description="テスト通知を送信")
    async def nudge_test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        success = await self.manager.send_nudge(
            interaction.user.id,
            "test",
            "📱 StudyBot テスト通知です！",
        )

        if success:
            await interaction.followup.send(
                embed=success_embed("テスト成功", "通知が送信されました！"),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                embed=error_embed(
                    "テスト失敗",
                    "通知の送信に失敗しました。\nWebhook URLが正しいか確認してください。",
                ),
                ephemeral=True,
            )

    @nudge_group.command(name="status", description="現在の通知設定を表示")
    async def nudge_status(self, interaction: discord.Interaction):
        config = await self.manager.get_config(interaction.user.id)

        if not config:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="📱 通知設定",
                    description="未設定です。`/nudge setup` で設定してください。",
                    color=COLORS["primary"],
                ),
                ephemeral=True,
            )
            return

        status = "✅ 有効" if config.get("enabled") else "❌ 無効"
        url = config.get("webhook_url", "")
        masked_url = url[:30] + "..." if len(url) > 30 else url

        embed = discord.Embed(
            title="📱 通知設定",
            color=COLORS["primary"],
        )
        embed.add_field(name="ステータス", value=status, inline=True)
        embed.add_field(name="Webhook", value=masked_url, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def send_nudge(self, user_id: int, event_type: str, message: str) -> None:
        """他Cogから呼び出し用の通知メソッド"""
        await self.manager.send_nudge(user_id, event_type, message)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = NudgeManager(db_pool)
    await bot.add_cog(PhoneNudgeCog(bot, manager))
