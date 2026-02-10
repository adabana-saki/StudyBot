"""ラーニングパス Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.learning_path_manager import LearningPathManager
from studybot.utils.embed_helper import error_embed, path_embed

logger = logging.getLogger(__name__)


class LearningPathCog(commands.Cog):
    """ラーニングパス機能"""

    def __init__(self, bot: commands.Bot, manager: LearningPathManager) -> None:
        self.bot = bot
        self.manager = manager

    path_group = app_commands.Group(name="path", description="ラーニングパス")

    @path_group.command(name="list", description="利用可能なラーニングパス一覧")
    @app_commands.describe(category="カテゴリでフィルタ")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="数学", value="math"),
            app_commands.Choice(name="英語", value="english"),
            app_commands.Choice(name="プログラミング", value="programming"),
        ]
    )
    async def path_list(
        self,
        interaction: discord.Interaction,
        category: str | None = None,
    ):
        await interaction.response.defer()
        paths = self.manager.get_paths(category)

        if not paths:
            await interaction.followup.send(
                embed=path_embed(
                    "ラーニングパス一覧",
                    "該当するパスがありません。",
                )
            )
            return

        embed = discord.Embed(
            title="ラーニングパス一覧",
            description="登録して学習を始めましょう！",
            color=COLORS["learning_path"],
        )
        for p in paths:
            embed.add_field(
                name=f"{p['emoji']} {p['name']}",
                value=(
                    f"ID: `{p['path_id']}`\n"
                    f"マイルストーン: {p['milestone_count']}個\n"
                    f"報酬: {p['reward_xp']}XP / {p['reward_coins']}コイン"
                ),
                inline=True,
            )
        embed.set_footer(text="/path enroll <path_id> で登録")
        await interaction.followup.send(embed=embed)

    @path_group.command(name="enroll", description="ラーニングパスに登録")
    @app_commands.describe(path_id="パスID")
    @app_commands.choices(
        path_id=[
            app_commands.Choice(name="数学基礎マスター", value="math_basics"),
            app_commands.Choice(name="英語初級コース", value="english_beginner"),
            app_commands.Choice(name="プログラミング入門", value="programming_intro"),
        ]
    )
    async def path_enroll(self, interaction: discord.Interaction, path_id: str):
        await interaction.response.defer()
        result = await self.manager.enroll(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            path_id=path_id,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("パス登録", result["error"]))
            return

        embed = path_embed(
            "パス登録完了！",
            (
                f"{result['emoji']} **{result['name']}** に登録しました！\n"
                f"マイルストーン: {result['milestone_count']}個\n\n"
                f"`/path progress {path_id}` で進捗を確認できます。"
            ),
        )
        await interaction.followup.send(embed=embed)

    @path_group.command(name="progress", description="ラーニングパスの進捗を表示")
    @app_commands.describe(path_id="パスID（省略で全パス表示）")
    async def path_progress(
        self,
        interaction: discord.Interaction,
        path_id: str | None = None,
    ):
        await interaction.response.defer()

        if path_id:
            result = await self.manager.get_progress(interaction.user.id, path_id)
            if "error" in result:
                await interaction.followup.send(embed=error_embed("進捗表示", result["error"]))
                return

            pct = (
                int(result["completed_count"] / result["total"] * 100) if result["total"] > 0 else 0
            )
            filled = int(15 * min(1.0, pct / 100))
            bar = "\u2588" * filled + "\u2591" * (15 - filled)

            status = "完了！" if result["path_completed"] else "進行中"
            embed = discord.Embed(
                title=f"{result['emoji']} {result['name']}",
                description=(
                    f"状態: **{status}**\n"
                    f"[{bar}] {pct}%\n"
                    f"({result['completed_count']}/{result['total']} マイルストーン)"
                ),
                color=COLORS["learning_path"],
            )

            for ms in result["milestones"]:
                if ms["completed"]:
                    icon = "\u2705"
                elif ms["current"]:
                    icon = "\u25b6\ufe0f"
                else:
                    icon = "\u2b1c"
                embed.add_field(
                    name=f"{icon} {ms['title']}",
                    value=f"{ms['description']} ({ms['target_minutes']}分)",
                    inline=False,
                )

            if result["path_completed"]:
                embed.set_footer(
                    text=(
                        f"報酬: {result['reward_xp']}XP / {result['reward_coins']}コイン 獲得済み"
                    )
                )
            await interaction.followup.send(embed=embed)
        else:
            # 全パス一覧
            results = await self.manager.get_user_paths_progress(interaction.user.id)
            if not results:
                await interaction.followup.send(
                    embed=path_embed(
                        "ラーニングパス進捗",
                        "登録中のパスがありません。\n`/path list` で一覧を確認しましょう！",
                    )
                )
                return

            embed = discord.Embed(
                title="ラーニングパス進捗一覧",
                color=COLORS["learning_path"],
            )
            for r in results:
                pct = int(r["completed_count"] / r["total"] * 100) if r["total"] > 0 else 0
                filled = int(10 * min(1.0, pct / 100))
                bar = "\u2588" * filled + "\u2591" * (10 - filled)
                status = "\u2705 完了" if r["path_completed"] else f"[{bar}] {pct}%"
                embed.add_field(
                    name=f"{r['emoji']} {r['name']}",
                    value=(f"{status}\n{r['completed_count']}/{r['total']} マイルストーン"),
                    inline=True,
                )
            await interaction.followup.send(embed=embed)

    @path_group.command(name="complete", description="現在のマイルストーンを完了")
    @app_commands.describe(path_id="パスID")
    @app_commands.choices(
        path_id=[
            app_commands.Choice(name="数学基礎マスター", value="math_basics"),
            app_commands.Choice(name="英語初級コース", value="english_beginner"),
            app_commands.Choice(name="プログラミング入門", value="programming_intro"),
        ]
    )
    async def path_complete(self, interaction: discord.Interaction, path_id: str):
        await interaction.response.defer()
        result = await self.manager.complete_current_milestone(
            user_id=interaction.user.id,
            path_id=path_id,
        )

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("マイルストーン完了", result["error"])
            )
            return

        pct = int(result["completed_count"] / result["total"] * 100) if result["total"] > 0 else 0
        filled = int(15 * min(1.0, pct / 100))
        bar = "\u2588" * filled + "\u2591" * (15 - filled)

        desc = (
            f"**{result['milestone_title']}** を完了しました！\n\n"
            f"[{bar}] {pct}%\n"
            f"({result['completed_count']}/{result['total']} マイルストーン)"
        )

        if result["path_completed"]:
            desc += (
                f"\n\n\U0001f389 **{result['path_name']}** を全て完了しました！\n"
                f"報酬: **{result['reward_xp']}XP** / "
                f"**{result['reward_coins']}コイン**"
            )

        embed = path_embed("マイルストーン完了！", desc)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = LearningPathManager(db_pool)
    await bot.add_cog(LearningPathCog(bot, manager))
