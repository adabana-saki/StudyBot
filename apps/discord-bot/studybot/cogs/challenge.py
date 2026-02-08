"""コホートチャレンジ Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS
from studybot.managers.challenge_manager import ChallengeManager
from studybot.utils.embed_helper import error_embed, success_embed

logger = logging.getLogger(__name__)


class ChallengeCog(commands.Cog):
    """コホートチャレンジ機能"""

    def __init__(self, bot: commands.Bot, manager: ChallengeManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.challenge_check.start()
        self.weekly_event_generator.start()

    async def cog_unload(self) -> None:
        self.challenge_check.cancel()
        self.weekly_event_generator.cancel()

    challenge_group = app_commands.Group(name="challenge", description="コホートチャレンジ")

    @challenge_group.command(name="create", description="チャレンジを作成")
    @app_commands.describe(
        name="チャレンジ名",
        duration="期間（日数）",
        goal_type="目標タイプ",
        goal_target="目標値",
    )
    @app_commands.choices(
        goal_type=[
            app_commands.Choice(name="学習時間（分）", value="study_minutes"),
            app_commands.Choice(name="セッション数", value="session_count"),
            app_commands.Choice(name="タスク完了数", value="tasks_completed"),
        ]
    )
    async def challenge_create(
        self,
        interaction: discord.Interaction,
        name: str,
        duration: int,
        goal_type: str = "study_minutes",
        goal_target: int = 600,
    ):
        await interaction.response.defer()
        result = await self.manager.create_challenge(
            creator_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id or 0,
            name=name,
            duration_days=duration,
            goal_type=goal_type,
            goal_target=goal_target,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("チャレンジ作成", result["error"]))
            return

        embed = discord.Embed(
            title="チャレンジ作成完了！",
            description=f"**{name}**",
            color=COLORS["challenge"],
        )
        embed.add_field(name="期間", value=f"{duration}日間", inline=True)
        embed.add_field(name="目標", value=f"{goal_target} {goal_type}", inline=True)
        embed.add_field(name="ID", value=f"#{result['challenge_id']}", inline=True)
        embed.set_footer(text="/challenge join で参加しよう！")
        await interaction.followup.send(embed=embed)

    @challenge_group.command(name="join", description="チャレンジに参加")
    @app_commands.describe(challenge_id="チャレンジID")
    async def challenge_join(self, interaction: discord.Interaction, challenge_id: int):
        await interaction.response.defer()
        result = await self.manager.join_challenge(
            challenge_id=challenge_id,
            user_id=interaction.user.id,
            username=interaction.user.display_name,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("チャレンジ参加", result["error"]))
            return

        embed = success_embed(
            "チャレンジ参加",
            f"**{result['name']}** に参加しました！\n参加者数: {result['participant_count']}人",
        )
        await interaction.followup.send(embed=embed)

        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_challenge_join(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild_id or 0,
                    username=interaction.user.display_name,
                    challenge_name=result["name"],
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

    @challenge_group.command(name="checkin", description="今日のチェックイン")
    @app_commands.describe(challenge_id="チャレンジID", progress="今日の進捗値")
    async def challenge_checkin(
        self,
        interaction: discord.Interaction,
        challenge_id: int,
        progress: int = 0,
    ):
        await interaction.response.defer()
        result = await self.manager.checkin(
            challenge_id=challenge_id,
            user_id=interaction.user.id,
            progress_delta=progress,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("チェックイン", result["error"]))
            return

        pct = (
            int(result["progress"] / result["goal_target"] * 100)
            if result["goal_target"] > 0
            else 0
        )
        filled = int(15 * min(1.0, pct / 100))
        bar = "\u2588" * filled + "\u2591" * (15 - filled)

        embed = discord.Embed(
            title="チェックイン完了！",
            color=COLORS["success"],
        )
        embed.add_field(
            name="進捗",
            value=(f"[{bar}] {pct}%\n{result['progress']}/{result['goal_target']}"),
            inline=False,
        )
        if result.get("completed"):
            embed.add_field(
                name="達成",
                value="目標達成！おめでとうございます！",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_challenge_checkin(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild_id or 0,
                    username=interaction.user.display_name,
                    challenge_name=result.get("challenge_name", ""),
                    progress=result["progress"],
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

    @challenge_group.command(name="list", description="チャレンジ一覧")
    async def challenge_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        challenges = await self.manager.list_challenges(interaction.guild_id or 0)

        if not challenges:
            await interaction.followup.send(
                embed=success_embed(
                    "チャレンジ一覧",
                    "まだチャレンジがありません。\n`/challenge create` で作成しましょう！",
                )
            )
            return

        embed = discord.Embed(title="チャレンジ一覧", color=COLORS["challenge"])
        status_icons = {
            "active": "🟢",
            "upcoming": "🔵",
            "completed": "⚪",
        }
        for c in challenges[:10]:
            status_icon = status_icons.get(c["status"], "?")
            embed.add_field(
                name=f"{status_icon} #{c['id']} {c['name']}",
                value=(
                    f"目標: {c['goal_target']} {c['goal_type']}\n"
                    f"参加者: {c['participant_count']}人\n"
                    f"期間: {c['duration_days']}日"
                ),
                inline=True,
            )
        await interaction.followup.send(embed=embed)

    @challenge_group.command(name="leaderboard", description="チャレンジリーダーボード")
    @app_commands.describe(challenge_id="チャレンジID")
    async def challenge_leaderboard(self, interaction: discord.Interaction, challenge_id: int):
        await interaction.response.defer()
        challenge = await self.manager.get_challenge(challenge_id)
        if not challenge:
            await interaction.followup.send(
                embed=error_embed("リーダーボード", "チャレンジが見つかりません")
            )
            return

        leaderboard = await self.manager.get_leaderboard(challenge_id)
        embed = discord.Embed(
            title=f"{challenge['name']} リーダーボード",
            color=COLORS["challenge"],
        )
        medals = ["🥇", "🥈", "🥉"]
        for i, entry in enumerate(leaderboard[:10]):
            medal = medals[i] if i < 3 else f"#{i + 1}"
            pct = (
                int(entry["progress"] / challenge["goal_target"] * 100)
                if challenge["goal_target"] > 0
                else 0
            )
            done = " (達成)" if entry["completed"] else ""
            embed.add_field(
                name=f"{medal} {entry['username']}{done}",
                value=(
                    f"進捗: {entry['progress']}/{challenge['goal_target']}"
                    f" ({pct}%)\n"
                    f"チェックイン: {entry['checkins']}回"
                ),
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @tasks.loop(hours=1)
    async def challenge_check(self):
        """期限切れチャレンジを自動完了"""
        for guild in self.bot.guilds:
            try:
                await self.manager.check_expired_challenges(guild.id)
            except Exception:
                logger.warning(
                    f"チャレンジチェック失敗: guild={guild.id}",
                    exc_info=True,
                )

    @challenge_check.before_loop
    async def before_challenge_check(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=24)
    async def weekly_event_generator(self):
        """毎日チェック: 月曜なら週次イベントを自動生成"""
        from datetime import date as date_type
        if date_type.today().weekday() != 0:  # 月曜のみ
            return

        for guild in self.bot.guilds:
            try:
                result = await self.manager.auto_generate_weekly_event(
                    guild_id=guild.id,
                    creator_id=self.bot.user.id,
                )
                if result:
                    logger.info(
                        "週次イベント自動生成: guild=%d, challenge=%s",
                        guild.id,
                        result["name"],
                    )
            except Exception:
                logger.warning(
                    "週次イベント生成失敗: guild=%d",
                    guild.id,
                    exc_info=True,
                )

    @weekly_event_generator.before_loop
    async def before_weekly_event_generator(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = ChallengeManager(db_pool)
    await bot.add_cog(ChallengeCog(bot, manager))
