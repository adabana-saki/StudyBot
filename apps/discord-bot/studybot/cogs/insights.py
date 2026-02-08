"""AI週次インサイト Cog"""

import logging
from datetime import time, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS
from studybot.managers.insights_manager import InsightsManager
from studybot.utils.embed_helper import error_embed

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))


class InsightsCog(commands.Cog):
    """AI週次インサイト機能"""

    def __init__(self, bot: commands.Bot, manager: InsightsManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.weekly_report.start()

    async def cog_unload(self) -> None:
        self.weekly_report.cancel()

    insights_group = app_commands.Group(name="insights", description="AIインサイト")

    @insights_group.command(name="preview", description="今週のインサイトをプレビュー")
    async def insights_preview(self, interaction: discord.Interaction):
        await interaction.response.defer()

        result = await self.manager.generate_insights(interaction.user.id)
        if "error" in result:
            await interaction.followup.send(embed=error_embed("インサイト", result["error"]))
            return

        embed = discord.Embed(
            title="🧠 AIインサイト",
            description=result.get("summary", ""),
            color=COLORS["insights"],
        )

        type_icons = {
            "pattern": "📊",
            "improvement": "📈",
            "achievement": "🏆",
            "warning": "⚠️",
        }

        for insight in result.get("insights", [])[:5]:
            icon = type_icons.get(insight.get("type", ""), "💡")
            confidence = int(insight.get("confidence", 0.5) * 100)
            embed.add_field(
                name=f"{icon} {insight.get('title', '')}",
                value=f"{insight.get('body', '')}\n信頼度: {confidence}%",
                inline=False,
            )

        stats = result.get("stats", {})
        embed.set_footer(
            text=f"総学習: {stats.get('total_combined_minutes', 0)}分 | "
            f"セッション: {stats.get('study_sessions', 0) + stats.get('pomodoro_sessions', 0)}回"
        )

        await interaction.followup.send(embed=embed)

        # イベント発行
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_insights_ready(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild_id or 0,
                    username=interaction.user.display_name,
                    insights_count=len(result.get("insights", [])),
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

    @tasks.loop(time=time(hour=9, minute=0, tzinfo=JST))
    async def weekly_report(self):
        """毎週月曜9:00 JSTに週次レポートを生成"""
        from datetime import datetime

        now = datetime.now(JST)
        if now.weekday() != 0:  # 月曜日のみ
            return

        logger.info("週次レポート生成開始")
        user_ids = await self.manager.get_active_user_ids()

        for user_id in user_ids:
            try:
                result = await self.manager.generate_insights(user_id)
                if "error" in result:
                    continue

                # DM送信
                user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                if user:
                    embed = discord.Embed(
                        title="🧠 週次インサイトレポート",
                        description=result.get("summary", ""),
                        color=COLORS["insights"],
                    )
                    for ins in result.get("insights", [])[:3]:
                        embed.add_field(
                            name=ins.get("title", ""),
                            value=ins.get("body", ""),
                            inline=False,
                        )
                    embed.set_footer(text="Webダッシュボードで詳細を確認できます")

                    try:
                        await user.send(embed=embed)
                        if result.get("report_id"):
                            await self.manager.mark_dm_sent(result["report_id"])
                    except discord.Forbidden:
                        logger.debug(f"DM送信不可: user={user_id}")

            except Exception:
                logger.warning(f"レポート生成失敗: user={user_id}", exc_info=True)

        logger.info(f"週次レポート完了: {len(user_ids)}ユーザー")

    @weekly_report.before_loop
    async def before_weekly_report(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    manager = InsightsManager(bot.db_pool)
    await bot.add_cog(InsightsCog(bot, manager))
