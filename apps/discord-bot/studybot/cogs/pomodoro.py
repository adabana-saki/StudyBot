"""ポモドーロタイマー Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS, POMODORO_DEFAULTS
from studybot.managers.pomodoro_manager import PomodoroManager
from studybot.utils.embed_helper import error_embed, success_embed

logger = logging.getLogger(__name__)


class PomodoroView(discord.ui.View):
    """ポモドーロ操作ボタン"""

    def __init__(self, cog: "PomodoroCog", user_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "このタイマーはあなたのものではありません。", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="⏸ 一時停止", style=discord.ButtonStyle.secondary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = await self.cog.manager.pause_session(self.user_id)
        if "error" in result:
            await interaction.response.send_message(result["error"], ephemeral=True)
        else:
            await interaction.response.send_message("⏸ 一時停止しました", ephemeral=True)

    @discord.ui.button(label="▶ 再開", style=discord.ButtonStyle.success)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = await self.cog.manager.resume_session(self.user_id)
        if "error" in result:
            await interaction.response.send_message(result["error"], ephemeral=True)
        else:
            await interaction.response.send_message("▶ 再開しました", ephemeral=True)

    @discord.ui.button(label="⏹ 停止", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = await self.cog.manager.stop_session(self.user_id)
        if "error" in result:
            await interaction.response.send_message(result["error"], ephemeral=True)
        else:
            embed = success_embed(
                "セッション終了",
                f"**{result['topic'] or '無題'}** - {result['total_minutes']}分間学習しました！",
            )
            await interaction.response.send_message(embed=embed)
            # XP付与（ゲーミフィケーション連携）
            gamification = self.cog.bot.get_cog("GamificationCog")
            if gamification and result["total_minutes"] >= result["work_minutes"]:
                await gamification.award_pomodoro_xp(self.user_id, interaction.channel)
            self.stop()


def _build_progress_bar(progress: float, width: int = 20) -> str:
    """進捗バーを生成"""
    filled = int(width * progress)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {int(progress * 100)}%"


def _format_time(seconds: int) -> str:
    """秒を mm:ss に変換"""
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


class PomodoroCog(commands.Cog):
    """ポモドーロタイマー機能"""

    def __init__(self, bot: commands.Bot, manager: PomodoroManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.timer_check.start()

    async def cog_unload(self) -> None:
        self.timer_check.cancel()

    pomodoro_group = app_commands.Group(name="pomodoro", description="ポモドーロタイマー")

    @pomodoro_group.command(name="start", description="ポモドーロセッションを開始")
    @app_commands.describe(
        topic="学習トピック",
        work_min="作業時間（分）",
        break_min="休憩時間（分）",
    )
    async def pomodoro_start(
        self,
        interaction: discord.Interaction,
        topic: str = "",
        work_min: int = POMODORO_DEFAULTS["work_minutes"],
        break_min: int = POMODORO_DEFAULTS["break_minutes"],
    ):
        await interaction.response.defer()

        result = await self.manager.start_session(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            topic=topic,
            work_minutes=work_min,
            break_minutes=break_min,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("開始失敗", result["error"]))
            return

        embed = discord.Embed(
            title="🍅 ポモドーロ開始！",
            description=(
                f"**トピック:** {topic or '未設定'}\n"
                f"**作業:** {work_min}分 | **休憩:** {break_min}分\n\n"
                f"{_build_progress_bar(0)}\n"
                f"残り: {_format_time(work_min * 60)}"
            ),
            color=COLORS["pomodoro"],
        )
        embed.set_footer(text=f"{interaction.user.display_name} のセッション")

        view = PomodoroView(self, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)

        # スマホ通知（phone_nudge連携）
        nudge_cog = self.bot.get_cog("PhoneNudgeCog")
        if nudge_cog:
            await nudge_cog.send_nudge(
                interaction.user.id,
                "study_start",
                f"🍅 ポモドーロ開始: {topic or '無題'} ({work_min}分)",
            )

    @pomodoro_group.command(name="pause", description="セッションを一時停止")
    async def pomodoro_pause(self, interaction: discord.Interaction):
        result = await self.manager.pause_session(interaction.user.id)
        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("一時停止失敗", result["error"]), ephemeral=True
            )
        else:
            await interaction.response.send_message("⏸ 一時停止しました", ephemeral=True)

    @pomodoro_group.command(name="resume", description="セッションを再開")
    async def pomodoro_resume(self, interaction: discord.Interaction):
        result = await self.manager.resume_session(interaction.user.id)
        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("再開失敗", result["error"]), ephemeral=True
            )
        else:
            await interaction.response.send_message("▶ 再開しました", ephemeral=True)

    @pomodoro_group.command(name="stop", description="セッションを停止")
    async def pomodoro_stop(self, interaction: discord.Interaction):
        result = await self.manager.stop_session(interaction.user.id)
        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("停止失敗", result["error"]), ephemeral=True
            )
            return

        embed = success_embed(
            "セッション終了",
            f"**{result['topic'] or '無題'}** - {result['total_minutes']}分間学習しました！",
        )
        await interaction.response.send_message(embed=embed)

        # XP付与
        gamification = self.bot.get_cog("GamificationCog")
        if gamification and result["total_minutes"] >= result["work_minutes"]:
            await gamification.award_pomodoro_xp(interaction.user.id, interaction.channel)

    @pomodoro_group.command(name="status", description="タイマーの状態を確認")
    async def pomodoro_status(self, interaction: discord.Interaction):
        status = self.manager.get_status(interaction.user.id)
        if not status:
            await interaction.response.send_message(
                "アクティブなセッションはありません。", ephemeral=True
            )
            return

        state_labels = {
            "working": "🔥 作業中",
            "break": "☕ 休憩中",
            "paused": "⏸ 一時停止",
        }

        embed = discord.Embed(
            title=f"🍅 {state_labels.get(status['state'], status['state'])}",
            description=(
                f"**トピック:** {status['topic'] or '未設定'}\n\n"
                f"{_build_progress_bar(status['progress'])}\n"
                f"残り: {_format_time(status['remaining_seconds'])}"
            ),
            color=COLORS["pomodoro"],
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(seconds=30)
    async def timer_check(self):
        """30秒ごとにタイマーをチェックして通知"""
        to_transition = []
        to_complete = []

        for user_id, _timer in self.manager.get_all_active_timers().items():
            status = self.manager.get_status(user_id)
            if not status or status["remaining_seconds"] > 0:
                continue

            if status["state"] == "working":
                to_transition.append(user_id)
            elif status["state"] == "break":
                to_complete.append(user_id)

        for user_id in to_transition:
            result = await self.manager.transition_to_break(user_id)
            if result:
                timer = self.manager.active_timers.get(user_id, {})
                channel_id = timer.get("channel_id")
                if channel_id:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        embed = discord.Embed(
                            title="☕ 休憩時間です！",
                            description=(
                                f"**{result['topic'] or '無題'}** の作業が終了しました。\n"
                                f"{result['break_minutes']}分間の休憩を取りましょう。"
                            ),
                            color=COLORS["success"],
                        )
                        await channel.send(f"<@{user_id}>", embed=embed)

        for user_id in to_complete:
            timer_info = self.manager.active_timers.get(user_id, {})
            channel_id = timer_info.get("channel_id")
            result = await self.manager.complete_session(user_id)
            if result and channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    embed = success_embed(
                        "ポモドーロ完了！🎉",
                        (
                            f"**{result['topic'] or '無題'}** のセッションが完了しました！\n"
                            f"合計 {result['total_minutes']}分間学習しました。"
                        ),
                    )
                    await channel.send(f"<@{user_id}>", embed=embed)

                    # XP付与
                    gamification = self.bot.get_cog("GamificationCog")
                    if gamification:
                        await gamification.award_pomodoro_xp(user_id, channel)

    @timer_check.before_loop
    async def before_timer_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = PomodoroManager(db_pool)
    await bot.add_cog(PomodoroCog(bot, manager))
