"""管理者 Cog

XP/コイン付与、ユーザーリセット、サーバー統計、チャンネル設定など
管理者専用コマンドを提供する。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import ADMIN_PERMISSIONS
from studybot.config.settings import settings
from studybot.managers.admin_manager import AdminManager
from studybot.utils.embed_helper import admin_embed, error_embed, success_embed

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


def is_admin():
    """管理者権限チェックデコレータ"""

    async def predicate(interaction: discord.Interaction) -> bool:
        # BOT_OWNER_ID チェック
        if interaction.user.id == getattr(settings, "BOT_OWNER_ID", 0):
            return True
        # サーバー管理者権限チェック
        if interaction.user.guild_permissions.administrator:
            return True
        # 管理者ロールチェック（server_settings から取得）
        return False

    return app_commands.check(predicate)


class AdminCog(commands.Cog):
    """管理者機能"""

    def __init__(self, bot: commands.Bot, manager: AdminManager) -> None:
        self.bot = bot
        self.manager = manager

    admin_group = app_commands.Group(
        name="admin",
        description="管理者コマンド",
        default_permissions=discord.Permissions(administrator=True),
    )

    @admin_group.command(name="grant_xp", description="ユーザーにXPを付与")
    @app_commands.describe(user="XPを付与するユーザー", amount="XP量")
    @is_admin()
    async def grant_xp(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
    ) -> None:
        if amount <= 0 or amount > ADMIN_PERMISSIONS["max_xp_grant"]:
            await interaction.response.send_message(
                embed=error_embed(
                    "エラー", f"XP量は1～{ADMIN_PERMISSIONS['max_xp_grant']}で指定してください。"
                ),
                ephemeral=True,
            )
            return

        gamification = self.bot.get_cog("GamificationCog")
        if not gamification:
            await interaction.response.send_message(
                embed=error_embed("エラー", "GamificationCogが読み込まれていません。"),
                ephemeral=True,
            )
            return

        await gamification.manager.ensure_user(user.id, user.display_name)
        reason = f"管理者付与 by {interaction.user}"
        result = await gamification.manager.add_xp(user.id, amount, reason)

        embed = admin_embed(
            "XP付与完了",
            f"**{user.display_name}** に **{amount:,} XP** を付与しました。\n"
            f"現在のXP: {result.get('total_xp', 0):,}"
            f" | Lv.{result.get('new_level', 0)}",
        )
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="grant_coins", description="ユーザーにコインを付与")
    @app_commands.describe(user="コインを付与するユーザー", amount="コイン量")
    @is_admin()
    async def grant_coins(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
    ) -> None:
        if amount <= 0 or amount > ADMIN_PERMISSIONS["max_coin_grant"]:
            await interaction.response.send_message(
                embed=error_embed(
                    "エラー",
                    f"コイン量は1～{ADMIN_PERMISSIONS['max_coin_grant']}で指定してください。",
                ),
                ephemeral=True,
            )
            return

        shop_cog = self.bot.get_cog("ShopCog")
        if not shop_cog:
            await interaction.response.send_message(
                embed=error_embed("エラー", "ShopCogが読み込まれていません。"),
                ephemeral=True,
            )
            return

        result = await shop_cog.award_coins(
            user.id, user.display_name, amount, f"管理者付与 by {interaction.user}"
        )

        embed = admin_embed(
            "コイン付与完了",
            f"**{user.display_name}** に **{amount:,} StudyCoin** を付与しました。\n"
            f"現在の残高: {result.get('balance', 0):,} 🪙",
        )
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="reset_user", description="ユーザーデータをリセット")
    @app_commands.describe(user="リセットするユーザー")
    @is_admin()
    async def reset_user(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        await interaction.response.defer()

        await self.manager.reset_user(user.id)

        embed = admin_embed(
            "ユーザーリセット完了",
            f"**{user.display_name}** のデータをリセットしました。\n"
            f"（XP, コイン, インベントリ, 実績）",
        )
        await interaction.followup.send(embed=embed)

    @admin_group.command(name="server_stats", description="サーバー全体の統計を表示")
    @is_admin()
    async def server_stats(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        stats = await self.manager.get_server_stats(interaction.guild_id)

        total_h = stats["total_minutes"] // 60
        total_m = stats["total_minutes"] % 60
        weekly_h = stats["weekly_minutes"] // 60
        weekly_m = stats["weekly_minutes"] % 60

        embed = admin_embed(
            f"サーバー統計 - {interaction.guild.name}",
            "",
        )
        embed.add_field(
            name="学習メンバー数",
            value=f"{stats['member_count']}人",
            inline=True,
        )
        embed.add_field(
            name="今週のアクティブ",
            value=f"{stats['weekly_active_members']}人",
            inline=True,
        )
        embed.add_field(
            name="累計学習時間",
            value=f"{total_h}時間{total_m}分",
            inline=True,
        )
        embed.add_field(
            name="今週の学習時間",
            value=f"{weekly_h}時間{weekly_m}分",
            inline=True,
        )
        embed.add_field(
            name="セッション数",
            value=f"{stats['total_sessions']}回",
            inline=True,
        )
        embed.add_field(
            name="完了タスク",
            value=f"{stats['tasks_completed']}件",
            inline=True,
        )
        embed.add_field(
            name="完了レイド",
            value=f"{stats['raids_completed']}回",
            inline=True,
        )
        await interaction.followup.send(embed=embed)

    @admin_group.command(name="set_study_channel", description="勉強チャンネルを設定")
    @app_commands.describe(channel="勉強チャンネル")
    @is_admin()
    async def set_study_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        await self.manager.update_setting(
            interaction.guild_id,
            "study_channels",
            [channel.id],
        )

        embed = success_embed(
            "設定更新",
            f"勉強チャンネルを {channel.mention} に設定しました。",
        )
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="set_vc_channel", description="VC追跡チャンネルを設定")
    @app_commands.describe(channel="VC追跡チャンネル")
    @is_admin()
    async def set_vc_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel,
    ) -> None:
        await self.manager.update_setting(
            interaction.guild_id,
            "vc_channels",
            [channel.id],
        )

        embed = success_embed(
            "設定更新",
            f"VC追跡チャンネルを {channel.mention} に設定しました。",
        )
        await interaction.response.send_message(embed=embed)

    @grant_xp.error
    @grant_coins.error
    @reset_user.error
    @server_stats.error
    @set_study_channel.error
    @set_vc_channel.error
    async def admin_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """管理者コマンド共通エラーハンドラ。

        権限チェック失敗時はユーザーに通知し、
        それ以外のエラーはログ出力後に汎用メッセージを返す。
        """
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=error_embed("権限エラー", "このコマンドは管理者のみ使用できます。"),
                ephemeral=True,
            )
        else:
            logger.error("管理者コマンドエラー: %s", error, exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=error_embed("エラー", "コマンドの実行中にエラーが発生しました。"),
                    ephemeral=True,
                )


async def setup(bot: commands.Bot) -> None:
    """AdminCogをBotに登録する。"""
    db_pool: asyncpg.Pool | None = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = AdminManager(db_pool)
    await bot.add_cog(AdminCog(bot, manager))
