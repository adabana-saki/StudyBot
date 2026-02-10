"""学習ログ & 統計 Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS, PERIOD_LABELS
from studybot.managers.study_manager import StudyManager
from studybot.utils.embed_helper import error_embed, study_embed

logger = logging.getLogger(__name__)


class StudyLogCog(commands.Cog):
    """学習ログ記録と統計表示"""

    def __init__(self, bot: commands.Bot, manager: StudyManager) -> None:
        self.bot = bot
        self.manager = manager

    study_group = app_commands.Group(name="study", description="学習ログ & 統計")

    @study_group.command(name="log", description="学習時間を記録")
    @app_commands.describe(
        duration="学習時間（分）",
        topic="学習トピック",
    )
    async def study_log(
        self,
        interaction: discord.Interaction,
        duration: int,
        topic: str = "",
    ):
        if duration <= 0 or duration > 720:
            await interaction.response.send_message(
                embed=error_embed("エラー", "学習時間は1〜720分で指定してください。"),
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        log_id = await self.manager.log_study(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id,
            duration_minutes=duration,
            topic=topic,
        )

        hours = duration // 60
        mins = duration % 60
        time_str = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"

        embed = study_embed(
            "📝 学習記録完了",
            f"**トピック:** {topic or '未設定'}\n**学習時間:** {time_str}\n**記録ID:** #{log_id}",
        )
        embed.set_footer(text=interaction.user.display_name)
        await interaction.followup.send(embed=embed)

        # イベント発行: 学習ログ
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_study_log(
                    user_id=interaction.user.id,
                    guild_id=getattr(interaction, "guild_id", 0) or 0,
                    topic=topic,
                    username=interaction.user.display_name,
                    duration_minutes=duration,
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

        # XP付与 (自己ベストチェックはaward_study_log_xp内で実行)
        gamification = self.bot.get_cog("GamificationCog")
        if gamification:
            try:
                await gamification.award_study_log_xp(
                    interaction.user.id, interaction.channel, duration
                )
            except Exception:
                logger.warning("学習ログのXP付与に失敗", exc_info=True)

        # チームクエスト連携: 学習時間
        team_cog = self.bot.get_cog("TeamCog")
        if team_cog:
            try:
                await team_cog.manager.update_team_quest_progress(
                    interaction.user.id, "team_study_minutes", duration
                )
            except Exception:
                logger.debug("チームクエスト更新失敗", exc_info=True)

        # フォーカスロック連携（レベル4: 学習完了コード）
        nudge_cog = self.bot.get_cog("PhoneNudgeCog")
        if nudge_cog:
            try:
                await nudge_cog.on_study_completed(interaction.user.id)
            except Exception:
                logger.warning("学習完了フック失敗", exc_info=True)

    @study_group.command(name="stats", description="学習統計を表示")
    @app_commands.describe(period="集計期間")
    @app_commands.choices(
        period=[
            app_commands.Choice(name="今日", value="daily"),
            app_commands.Choice(name="今週", value="weekly"),
            app_commands.Choice(name="今月", value="monthly"),
            app_commands.Choice(name="全期間", value="all_time"),
        ]
    )
    async def study_stats(
        self,
        interaction: discord.Interaction,
        period: str = "weekly",
    ):
        await interaction.response.defer()

        stats = await self.manager.get_stats(interaction.user.id, interaction.guild_id, period)

        total = int(stats["total_minutes"])
        hours = total // 60
        mins = total % 60
        time_str = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"
        avg = int(stats["avg_minutes"])

        period_label = PERIOD_LABELS.get(period, period)

        embed = discord.Embed(
            title=f"📊 学習統計 - {period_label}",
            color=COLORS["study"],
        )
        embed.add_field(name="合計学習時間", value=time_str, inline=True)
        embed.add_field(name="セッション数", value=f"{stats['session_count']}回", inline=True)
        embed.add_field(name="平均学習時間", value=f"{avg}分/回", inline=True)
        embed.set_footer(text=interaction.user.display_name)

        await interaction.followup.send(embed=embed)

    @study_group.command(name="chart", description="学習チャートを生成")
    @app_commands.describe(
        chart_type="チャートの種類",
        days="過去何日分のデータを表示するか",
    )
    @app_commands.choices(
        chart_type=[
            app_commands.Choice(name="折れ線グラフ", value="line"),
            app_commands.Choice(name="棒グラフ", value="bar"),
            app_commands.Choice(name="トピック別円グラフ", value="pie"),
        ]
    )
    async def study_chart(
        self,
        interaction: discord.Interaction,
        chart_type: str = "line",
        days: int = 14,
    ):
        if days < 1 or days > 90:
            await interaction.response.send_message(
                embed=error_embed("エラー", "日数は1〜90で指定してください。"),
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        if chart_type == "pie":
            buf = await self.manager.generate_topic_chart(
                interaction.user.id, interaction.guild_id, days
            )
        else:
            buf = await self.manager.generate_chart(
                interaction.user.id, interaction.guild_id, chart_type, days
            )

        if not buf:
            await interaction.followup.send(
                embed=error_embed("データなし", "指定期間にデータがありません。")
            )
            return

        file = discord.File(buf, filename="study_chart.png")
        embed = discord.Embed(
            title=f"📈 学習チャート（過去{days}日間）",
            color=COLORS["study"],
        )
        embed.set_image(url="attachment://study_chart.png")
        embed.set_footer(text=interaction.user.display_name)

        await interaction.followup.send(embed=embed, file=file)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = StudyManager(db_pool)
    await bot.add_cog(StudyLogCog(bot, manager))
