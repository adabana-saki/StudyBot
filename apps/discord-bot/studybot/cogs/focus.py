"""フォーカスモード Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COIN_REWARDS, FOCUS_DEFAULTS
from studybot.managers.focus_manager import FocusManager
from studybot.utils.embed_helper import error_embed, focus_embed, success_embed

logger = logging.getLogger(__name__)


def _format_time(seconds: int) -> str:
    """秒を mm:ss に変換"""
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def _build_progress_bar(progress: float, width: int = 20) -> str:
    """進捗バーを生成"""
    filled = int(width * progress)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    return f"[{bar}] {int(progress * 100)}%"


class FocusCog(commands.Cog):
    """フォーカスモード機能"""

    def __init__(self, bot: commands.Bot, manager: FocusManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.focus_check.start()

    async def cog_unload(self) -> None:
        self.focus_check.cancel()

    focus_group = app_commands.Group(name="focus", description="フォーカスモード")

    @focus_group.command(name="start", description="フォーカスモードを開始")
    @app_commands.describe(duration="フォーカス時間（分）デフォルト60分")
    async def focus_start(
        self,
        interaction: discord.Interaction,
        duration: int = FOCUS_DEFAULTS["default_duration"],
    ):
        await interaction.response.defer()

        result = await self.manager.start_focus(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id,
            duration_minutes=duration,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("開始失敗", result["error"]))
            return

        hours = duration // 60
        mins = duration % 60
        time_str = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"

        end_time_str = discord.utils.format_dt(result["end_time"], style="T")

        embed = focus_embed(
            "フォーカスモード開始！",
            (
                f"**集中時間:** {time_str}\n"
                f"**終了予定:** {end_time_str}\n\n"
                f"{_build_progress_bar(0)}\n"
                f"残り: {_format_time(duration * 60)}\n\n"
                f"集中して頑張りましょう！"
            ),
        )
        embed.set_footer(text=interaction.user.display_name)

        await interaction.followup.send(embed=embed)

        # イベント発行: フォーカス開始
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_focus_start(
                    user_id=interaction.user.id,
                    guild_id=getattr(interaction, "guild_id", 0) or 0,
                    username=interaction.user.display_name,
                    duration_minutes=duration,
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

        # セッション同期
        if hasattr(self.bot, "session_sync") and self.bot.session_sync:
            try:
                await self.bot.session_sync.register_session(
                    user_id=interaction.user.id,
                    username=interaction.user.display_name,
                    session_type="focus",
                    source="discord",
                    duration_minutes=duration,
                )
            except Exception:
                logger.warning("セッション同期失敗", exc_info=True)

    @focus_group.command(name="whitelist", description="フォーカス中に許可するチャンネルを追加")
    @app_commands.describe(channel="許可するテキストチャンネル")
    async def focus_whitelist(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        result = await self.manager.add_whitelist(interaction.user.id, channel.id)

        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("追加失敗", result["error"]),
                ephemeral=True,
            )
            return

        embed = focus_embed(
            "ホワイトリスト更新",
            (
                f"**{channel.mention}** をホワイトリストに追加しました。\n"
                f"現在のホワイトリスト: {result['whitelist_count']}チャンネル"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @focus_group.command(name="end", description="フォーカスモードを終了")
    async def focus_end(self, interaction: discord.Interaction):
        result = await self.manager.end_focus(interaction.user.id)

        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("終了失敗", result["error"]),
                ephemeral=True,
            )
            return

        actual = result["duration_actual"]
        hours = actual // 60
        mins = actual % 60
        time_str = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"

        if result["completed"]:
            description = (
                f"フォーカスセッションを完了しました！\n"
                f"**集中時間:** {time_str}\n"
                f"**予定時間:** {result['duration_planned']}分\n\n"
                f"お疲れ様でした！"
            )
            embed = success_embed("フォーカス完了！", description)

            # コイン付与
            shop_cog = self.bot.get_cog("ShopCog")
            if shop_cog:
                try:
                    await shop_cog.award_coins(
                        interaction.user.id,
                        interaction.user.display_name,
                        COIN_REWARDS["focus_complete"],
                        "フォーカスセッション完了",
                    )
                    embed.add_field(
                        name="報酬",
                        value=f"+{COIN_REWARDS['focus_complete']} StudyCoin",
                        inline=False,
                    )
                except Exception:
                    logger.warning("フォーカス完了のコイン付与に失敗", exc_info=True)
        else:
            description = (
                f"フォーカスセッションを途中で終了しました。\n"
                f"**集中時間:** {time_str}\n"
                f"**予定時間:** {result['duration_planned']}分\n\n"
                f"次回は最後まで頑張りましょう！"
            )
            embed = focus_embed("フォーカス終了", description)

        embed.set_footer(text=interaction.user.display_name)
        await interaction.response.send_message(embed=embed)

        # イベント発行: フォーカス終了
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_focus_end(
                    user_id=interaction.user.id,
                    guild_id=getattr(interaction, "guild_id", 0) or 0,
                    username=interaction.user.display_name,
                    duration_minutes=result.get("duration_actual", 0),
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

        # セッション同期終了
        if hasattr(self.bot, "session_sync") and self.bot.session_sync:
            try:
                await self.bot.session_sync.end_session(interaction.user.id)
            except Exception:
                logger.warning("セッション同期終了失敗", exc_info=True)

    @focus_group.command(name="status", description="フォーカスの状態を確認")
    async def focus_status(self, interaction: discord.Interaction):
        status = self.manager.get_status(interaction.user.id)

        if not status:
            await interaction.response.send_message(
                embed=focus_embed(
                    "フォーカスステータス",
                    "アクティブなフォーカスセッションはありません。",
                ),
                ephemeral=True,
            )
            return

        remaining = status["remaining_seconds"]
        end_time_str = discord.utils.format_dt(status["end_time"], style="T")

        whitelist_text = ""
        if status["whitelisted_channels"]:
            channels = [f"<#{ch_id}>" for ch_id in status["whitelisted_channels"]]
            whitelist_text = f"\n**ホワイトリスト:** {', '.join(channels)}"

        embed = focus_embed(
            "フォーカス中",
            (
                f"**集中時間:** {status['duration_minutes']}分\n"
                f"**終了予定:** {end_time_str}\n\n"
                f"{_build_progress_bar(status['progress'])}\n"
                f"残り: {_format_time(remaining)}"
                f"{whitelist_text}"
            ),
        )
        embed.set_footer(text=interaction.user.display_name)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(seconds=30)
    async def focus_check(self):
        """30秒ごとにフォーカスセッションの完了をチェック"""
        try:
            expired = await self.manager.check_sessions()
        except Exception:
            logger.error("フォーカスセッションチェック中にエラー", exc_info=True)
            return

        for session in expired:
            try:
                user_id = session["user_id"]
                guild_id = session["guild_id"]
                duration = session["duration_minutes"]

                # ユーザーにDMまたはチャンネルで通知
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue

                member = guild.get_member(user_id)
                if not member:
                    continue

                hours = duration // 60
                mins = duration % 60
                time_str = f"{hours}時間{mins}分" if hours > 0 else f"{mins}分"

                embed = success_embed(
                    "フォーカス完了！",
                    (f"**{time_str}**のフォーカスセッションが完了しました！\nお疲れ様でした！"),
                )

                # コイン付与
                coin_text = ""
                shop_cog = self.bot.get_cog("ShopCog")
                if shop_cog:
                    try:
                        await shop_cog.award_coins(
                            user_id,
                            "",
                            COIN_REWARDS["focus_complete"],
                            "フォーカスセッション完了",
                        )
                        coin_text = f"\n+{COIN_REWARDS['focus_complete']} StudyCoin を獲得！"
                    except Exception:
                        logger.warning("フォーカス完了のコイン付与に失敗", exc_info=True)

                if coin_text:
                    embed.add_field(name="報酬", value=coin_text, inline=False)

                # イベント発行: フォーカス終了（自然完了）
                if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
                    try:
                        await self.bot.event_publisher.emit_focus_end(
                            user_id=user_id,
                            guild_id=guild_id or 0,
                            username=member.display_name,
                            duration_minutes=duration,
                        )
                    except Exception:
                        logger.warning("イベント発行失敗", exc_info=True)

                # セッション同期終了
                if hasattr(self.bot, "session_sync") and self.bot.session_sync:
                    try:
                        await self.bot.session_sync.end_session(user_id)
                    except Exception:
                        logger.warning("セッション同期終了失敗", exc_info=True)

                # DMで通知を試みる
                try:
                    await member.send(embed=embed)
                except discord.Forbidden:
                    logger.debug(f"ユーザー {user_id} へのDM送信に失敗")

            except Exception:
                logger.error(
                    f"フォーカスセッション完了処理中にエラー (user_id={session.get('user_id')})",
                    exc_info=True,
                )

    @focus_check.before_loop
    async def before_focus_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = FocusManager(db_pool)
    await bot.add_cog(FocusCog(bot, manager))
