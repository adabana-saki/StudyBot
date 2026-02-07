"""学習プラン Cog"""

import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.plan_manager import PlanManager
from studybot.utils.embed_helper import error_embed, study_embed, success_embed

logger = logging.getLogger(__name__)


class StudyPlanCog(commands.Cog):
    """学習プラン機能"""

    def __init__(self, bot: commands.Bot, manager: PlanManager) -> None:
        self.bot = bot
        self.manager = manager

    plan_group = app_commands.Group(name="plan", description="学習プラン")

    @plan_group.command(name="create", description="AIで学習プランを作成")
    @app_commands.describe(
        subject="科目",
        goal="学習目標",
        deadline="期限（YYYY-MM-DD）",
    )
    async def plan_create(
        self,
        interaction: discord.Interaction,
        subject: str,
        goal: str,
        deadline: str | None = None,
    ):
        # 期限パース
        parsed_deadline = None
        if deadline:
            try:
                parsed_deadline = (
                    datetime.strptime(deadline.strip(), "%Y-%m-%d").replace(tzinfo=UTC).date()
                )
            except ValueError:
                await interaction.response.send_message(
                    embed=error_embed("エラー", "期限の形式: YYYY-MM-DD"),
                    ephemeral=True,
                )
                return

        await interaction.response.defer()

        result = await self.manager.create_plan(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            subject=subject,
            goal=goal,
            deadline=parsed_deadline,
        )

        if not result:
            await interaction.followup.send(
                embed=error_embed("エラー", "学習プランの作成に失敗しました。")
            )
            return

        plan = result.get("plan", {})
        tasks = result.get("tasks", [])

        task_lines = []
        for task in tasks:
            status_icon = "⬜"
            task_lines.append(
                f"{status_icon} `#{task['id']}` **{task['title']}**\n"
                f"  {task.get('description', '')}"
            )

        deadline_str = (
            plan.get("deadline").strftime("%Y/%m/%d") if plan.get("deadline") else "未設定"
        )

        embed = discord.Embed(
            title=f"📋 学習プラン: {plan.get('subject', subject)}",
            description=(
                f"**目標:** {plan.get('goal', goal)}\n"
                f"**期限:** {deadline_str}\n\n"
                "**タスク:**\n" + "\n".join(task_lines)
                if task_lines
                else "タスクの生成に失敗しました。"
            ),
            color=COLORS["study"],
        )
        embed.set_footer(text=interaction.user.display_name)
        await interaction.followup.send(embed=embed)

    @plan_group.command(name="view", description="現在の学習プランを表示")
    async def plan_view(self, interaction: discord.Interaction):
        await interaction.response.defer()

        result = await self.manager.get_current_plan(interaction.user.id)

        if not result:
            await interaction.followup.send(
                embed=study_embed(
                    "📋 学習プラン",
                    "アクティブな学習プランがありません。\n`/plan create` で作成しましょう！",
                )
            )
            return

        plan = result.get("plan", {})
        tasks = result.get("tasks", [])

        task_lines = []
        for task in tasks:
            status_icon = "✅" if task["status"] == "completed" else "⬜"
            task_lines.append(
                f"{status_icon} `#{task['id']}` **{task['title']}**\n"
                f"  {task.get('description', '')}"
            )

        deadline_str = (
            plan.get("deadline").strftime("%Y/%m/%d") if plan.get("deadline") else "未設定"
        )

        embed = discord.Embed(
            title=f"📋 学習プラン: {plan.get('subject', '')}",
            description=(
                f"**目標:** {plan.get('goal', '')}\n"
                f"**期限:** {deadline_str}\n\n"
                "**タスク:**\n" + "\n".join(task_lines)
            ),
            color=COLORS["study"],
        )
        embed.set_footer(text=interaction.user.display_name)
        await interaction.followup.send(embed=embed)

    @plan_group.command(name="progress", description="学習プランの進捗を表示")
    async def plan_progress(self, interaction: discord.Interaction):
        await interaction.response.defer()

        result = await self.manager.get_progress_with_feedback(interaction.user.id)

        if "error" in result:
            await interaction.followup.send(embed=error_embed("エラー", result["error"]))
            return

        plan = result["plan"]
        progress = result["progress"]
        feedback = result.get("feedback")

        # プログレスバー
        pct = progress["percentage"]
        bar_filled = int(pct // 10)
        bar_empty = 10 - bar_filled
        bar = "█" * bar_filled + "░" * bar_empty

        description = (
            f"**科目:** {plan.get('subject', '')}\n"
            f"**目標:** {plan.get('goal', '')}\n\n"
            f"**進捗:** {progress['completed']}/{progress['total']}\n"
            f"{bar} {pct}%"
        )

        if feedback:
            description += f"\n\n**AIフィードバック:**\n{feedback}"

        embed = discord.Embed(
            title="📊 学習プラン進捗",
            description=description,
            color=COLORS["study"],
        )
        embed.set_footer(text=interaction.user.display_name)
        await interaction.followup.send(embed=embed)

    @plan_group.command(name="complete", description="プランのタスクを完了")
    @app_commands.describe(task_id="タスクID")
    async def plan_complete(self, interaction: discord.Interaction, task_id: int):
        await interaction.response.defer()

        result = await self.manager.complete_task(interaction.user.id, task_id)

        if "error" in result:
            await interaction.followup.send(embed=error_embed("エラー", result["error"]))
            return

        task = result["task"]
        progress = result["progress"]

        pct = progress["percentage"]
        bar_filled = int(pct // 10)
        bar_empty = 10 - bar_filled
        bar = "█" * bar_filled + "░" * bar_empty

        embed = success_embed(
            "タスク完了！",
            f"**{task['title']}** を完了しました！\n\n"
            f"進捗: {progress['completed']}/{progress['total']}\n"
            f"{bar} {pct}%",
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = PlanManager(db_pool)
    await bot.add_cog(StudyPlanCog(bot, manager))
