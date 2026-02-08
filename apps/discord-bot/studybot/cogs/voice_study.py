"""VCスタディ追跡 Cog

ボイスチャンネルでの勉強セッションを自動追跡し、
XP・コイン付与とDM通知を行う。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COIN_REWARDS, VC_DEFAULTS, XP_REWARDS
from studybot.managers.voice_manager import VoiceManager
from studybot.utils.embed_helper import success_embed, vc_embed

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


class VoiceStudyCog(commands.Cog):
    """VCスタディ追跡機能"""

    def __init__(self, bot: commands.Bot, manager: VoiceManager) -> None:
        self.bot = bot
        self.manager = manager

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """VC参加/退出を検知して勉強時間を追跡"""
        if member.bot:
            return

        # AFK チャンネル除外
        guild = member.guild
        afk_channel = guild.afk_channel

        # サーバー設定を確認
        settings = await self.manager.get_server_settings(guild.id)
        if settings and not settings.get("vc_tracking_enabled", True):
            return

        # 特定チャンネルのみ追跡（設定がある場合）
        vc_channels = settings.get("vc_channels", []) if settings else []

        # VC参加
        if before.channel is None and after.channel is not None:
            # AFKチャンネルは除外
            if afk_channel and after.channel.id == afk_channel.id:
                return
            # 特定チャンネルフィルタ
            if vc_channels and after.channel.id not in vc_channels:
                return

            self.manager.start_session(member.id, guild.id, after.channel.id)

        # VC退出
        elif before.channel is not None and after.channel is None:
            min_minutes = VC_DEFAULTS["min_duration_minutes"]
            if settings and settings.get("min_vc_minutes"):
                min_minutes = settings["min_vc_minutes"]

            result = await self.manager.end_session(member.id, min_minutes)
            if result:
                await self._on_session_complete(member, result)

        # チャンネル移動
        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel.id != after.channel.id
        ):
            # AFKチャンネルに移動した場合はセッション終了
            if afk_channel and after.channel.id == afk_channel.id:
                min_minutes = VC_DEFAULTS["min_duration_minutes"]
                result = await self.manager.end_session(member.id, min_minutes)
                if result:
                    await self._on_session_complete(member, result)
            # 追跡対象外チャンネルに移動した場合もセッション終了
            elif vc_channels and after.channel.id not in vc_channels:
                min_minutes = VC_DEFAULTS["min_duration_minutes"]
                result = await self.manager.end_session(member.id, min_minutes)
                if result:
                    await self._on_session_complete(member, result)
            # 追跡対象に新規参加
            elif not self.manager.is_tracking(member.id):
                if not vc_channels or after.channel.id in vc_channels:
                    self.manager.start_session(member.id, guild.id, after.channel.id)

    async def _on_session_complete(self, member: discord.Member, result: dict) -> None:
        """VCセッション完了時の処理"""
        duration = result["duration_minutes"]
        hours = duration // 60
        mins = duration % 60
        time_str = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"

        # XP付与（30分あたり）
        xp_units = max(1, duration // 30)
        gamification = self.bot.get_cog("GamificationCog")
        if gamification:
            try:
                xp_amount = XP_REWARDS["vc_study"] * xp_units
                await gamification.manager.add_xp(member.id, xp_amount, "VC勉強")
            except Exception:
                logger.warning("VC勉強のXP付与に失敗 (user=%d)", member.id, exc_info=True)

        # コイン付与
        shop_cog = self.bot.get_cog("ShopCog")
        if shop_cog:
            try:
                coin_amount = COIN_REWARDS["vc_study"] * xp_units
                await shop_cog.award_coins(member.id, member.display_name, coin_amount, "VC勉強")
            except Exception:
                logger.warning("VC勉強のコイン付与に失敗 (user=%d)", member.id, exc_info=True)

        # DMで通知を試みる
        try:
            embed = success_embed(
                "VC勉強記録",
                f"**{time_str}**のVC勉強セッションを自動記録しました！",
            )
            await member.send(embed=embed)
        except discord.Forbidden:
            logger.debug("ユーザー %d へのDM送信に失敗", member.id)

    vc_group = app_commands.Group(name="vc", description="VC勉強追跡")

    @vc_group.command(name="status", description="現在VCで勉強中のメンバー一覧")
    async def vc_status(self, interaction: discord.Interaction) -> None:
        sessions = self.manager.get_active_sessions()
        if not sessions:
            await interaction.response.send_message(
                embed=vc_embed("VC勉強", "現在VCで勉強中のメンバーはいません。"),
                ephemeral=True,
            )
            return

        lines = []
        now = datetime.now(UTC)
        for user_id, session in sessions.items():
            if session["guild_id"] != interaction.guild_id:
                continue
            elapsed = int((now - session["started_at"]).total_seconds() / 60)
            channel = self.bot.get_channel(session["channel_id"])
            channel_name = channel.name if channel else "不明"
            lines.append(f"<@{user_id}> - 🎙️ {channel_name} ({elapsed}分経過)")

        if not lines:
            await interaction.response.send_message(
                embed=vc_embed("VC勉強", "このサーバーでVCで勉強中のメンバーはいません。"),
                ephemeral=True,
            )
            return

        embed = vc_embed("VC勉強中のメンバー", "\n".join(lines))
        embed.set_footer(text=f"{len(lines)}人が勉強中")
        await interaction.response.send_message(embed=embed)

    @vc_group.command(name="stats", description="VC勉強時間統計")
    @app_commands.describe(days="過去何日分の統計を表示するか")
    async def vc_stats(self, interaction: discord.Interaction, days: int = 30) -> None:
        await interaction.response.defer()

        stats = await self.manager.get_stats(interaction.user.id, interaction.guild_id, days)

        total = int(stats["total_minutes"])
        hours = total // 60
        mins = total % 60
        time_str = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"
        avg = int(stats["avg_minutes"])

        embed = vc_embed(f"VC勉強統計（過去{days}日間）", "")
        embed.add_field(name="合計VC勉強時間", value=time_str, inline=True)
        embed.add_field(name="セッション数", value=f"{stats['session_count']}回", inline=True)
        embed.add_field(name="平均セッション", value=f"{avg}分/回", inline=True)

        # ランキングも表示
        ranking = await self.manager.get_ranking(interaction.guild_id, days)
        if ranking:
            rank_lines = []
            medals = ["🥇", "🥈", "🥉"]
            for i, entry in enumerate(ranking[:5]):
                medal = medals[i] if i < 3 else f"**{i + 1}.**"
                total_min = entry["total_minutes"]
                h, m = divmod(total_min, 60)
                rank_lines.append(f"{medal} {entry['username']} - {h}時間{m}分")
            embed.add_field(
                name="VC勉強ランキング",
                value="\n".join(rank_lines),
                inline=False,
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """VoiceStudyCogをBotに登録する。"""
    db_pool: asyncpg.Pool | None = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = VoiceManager(db_pool)
    await bot.add_cog(VoiceStudyCog(bot, manager))
