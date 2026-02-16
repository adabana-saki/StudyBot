"""スタディバディ Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.buddy_manager import BuddyManager
from studybot.utils.embed_helper import error_embed, success_embed

logger = logging.getLogger(__name__)


class BuddyCog(commands.Cog):
    """スタディバディマッチング"""

    def __init__(self, bot: commands.Bot, manager: BuddyManager) -> None:
        self.bot = bot
        self.manager = manager

    buddy_group = app_commands.Group(name="buddy", description="スタディバディ")

    @buddy_group.command(name="find", description="スタディバディを探す")
    @app_commands.describe(subject="マッチングしたい教科（オプション）")
    async def buddy_find(self, interaction: discord.Interaction, subject: str | None = None):
        await interaction.response.defer()
        result = await self.manager.find_buddy(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id or 0,
            subject=subject,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("バディ検索", result["error"]))
            return

        embed = discord.Embed(
            title="🤝 バディが見つかりました！",
            color=COLORS["buddy"],
        )
        embed.add_field(name="パートナー", value=result["partner_name"], inline=True)
        embed.add_field(
            name="互換スコア",
            value=f"{int(result['compatibility_score'] * 100)}%",
            inline=True,
        )
        if result.get("subject"):
            embed.add_field(name="教科", value=result["subject"], inline=True)

        await interaction.followup.send(embed=embed)

        # イベント発行
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_buddy_match(
                    user_a=interaction.user.id,
                    user_b=result["partner_id"],
                    guild_id=interaction.guild_id or 0,
                    subject=subject or "",
                    score=result["compatibility_score"],
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

    @buddy_group.command(name="status", description="現在のバディマッチ状況")
    async def buddy_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        matches = await self.manager.get_active_matches(interaction.user.id)

        if not matches:
            await interaction.followup.send(
                embed=success_embed(
                    "バディステータス",
                    "現在アクティブなマッチはありません。\n`/buddy find` で探してみましょう！",
                )
            )
            return

        embed = discord.Embed(title="🤝 アクティブなバディ", color=COLORS["buddy"])
        for m in matches[:5]:
            partner = m["username_b"] if m["user_a"] == interaction.user.id else m["username_a"]
            embed.add_field(
                name=partner,
                value=(
                    f"教科: {m.get('subject') or '指定なし'}\n"
                    f"互換: {int(m['compatibility_score'] * 100)}%"
                ),
                inline=True,
            )
        await interaction.followup.send(embed=embed)

    @buddy_group.command(name="history", description="バディマッチ履歴")
    async def buddy_history(self, interaction: discord.Interaction):
        await interaction.response.defer()
        history = await self.manager.get_match_history(interaction.user.id)

        if not history:
            await interaction.followup.send(
                embed=success_embed("バディ履歴", "まだマッチ履歴がありません。")
            )
            return

        embed = discord.Embed(title="📋 バディ履歴", color=COLORS["buddy"])
        for m in history[:10]:
            partner = m["username_b"] if m["user_a"] == interaction.user.id else m["username_a"]
            status_label = "🟢 アクティブ" if m["status"] == "active" else "⚪ 終了"
            embed.add_field(
                name=f"{partner} ({status_label})",
                value=(
                    f"教科: {m.get('subject') or '指定なし'}"
                    f" | 互換: {int(m['compatibility_score'] * 100)}%"
                ),
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @buddy_group.command(name="profile", description="バディプロフィール設定")
    @app_commands.describe(
        subjects="教科（カンマ区切り、例: 数学,英語,物理）",
        times="希望時間帯（カンマ区切り、例: 朝,昼,夜）",
        style="勉強スタイル",
    )
    @app_commands.choices(
        style=[
            app_commands.Choice(name="集中型", value="focused"),
            app_commands.Choice(name="協力型", value="collaborative"),
            app_commands.Choice(name="自由型", value="flexible"),
        ]
    )
    async def buddy_profile(
        self,
        interaction: discord.Interaction,
        subjects: str = "",
        times: str = "",
        style: str = "focused",
    ):
        await interaction.response.defer()
        subject_list = [s.strip() for s in subjects.split(",") if s.strip()] if subjects else []
        time_list = [t.strip() for t in times.split(",") if t.strip()] if times else []

        await self.manager.update_profile(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            subjects=subject_list,
            preferred_times=time_list,
            study_style=style,
        )

        embed = success_embed(
            "プロフィール更新",
            f"教科: {', '.join(subject_list) or 'なし'}\n"
            f"時間帯: {', '.join(time_list) or 'なし'}\n"
            f"スタイル: {style}",
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    db_pool = getattr(bot, "db_pool", None)
    if db_pool is None:
        logger.error("db_pool が未初期化のため BuddyCog をロードできません")
        return
    manager = BuddyManager(db_pool)
    await bot.add_cog(BuddyCog(bot, manager))
