"""To-Do管理 Cog"""

import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS, PRIORITY_LABELS
from studybot.managers.todo_manager import TodoManager
from studybot.utils.embed_helper import error_embed, info_embed, success_embed

logger = logging.getLogger(__name__)


class TodoModal(discord.ui.Modal, title="タスク追加"):
    """タスク追加用モーダル"""

    task_title = discord.ui.TextInput(
        label="タスク名",
        placeholder="例: 数学の宿題を終わらせる",
        max_length=300,
    )
    priority_input = discord.ui.TextInput(
        label="優先度（1=高, 2=中, 3=低）",
        placeholder="2",
        default="2",
        max_length=1,
    )
    deadline_input = discord.ui.TextInput(
        label="期限（YYYY-MM-DD HH:MM）※任意",
        placeholder="2025-03-15 18:00",
        required=False,
        max_length=20,
    )

    def __init__(self, cog: "TodoCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        # 優先度バリデーション
        try:
            priority = int(self.priority_input.value)
            if priority not in (1, 2, 3):
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed("エラー", "優先度は 1, 2, 3 のいずれかです。"),
                ephemeral=True,
            )
            return

        # 期限パース
        deadline = None
        if self.deadline_input.value.strip():
            try:
                deadline = datetime.strptime(
                    self.deadline_input.value.strip(), "%Y-%m-%d %H:%M"
                ).replace(tzinfo=UTC)
            except ValueError:
                await interaction.response.send_message(
                    embed=error_embed(
                        "エラー", "期限の形式が正しくありません。\n例: 2025-03-15 18:00"
                    ),
                    ephemeral=True,
                )
                return

        await interaction.response.defer()

        todo_id = await self.cog.manager.add_todo(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id,
            title=self.task_title.value,
            priority=priority,
            deadline=deadline,
        )

        deadline_str = deadline.strftime("%Y/%m/%d %H:%M") if deadline else "なし"
        embed = success_embed(
            "タスク追加完了",
            f"**{self.task_title.value}**\n"
            f"優先度: {PRIORITY_LABELS[priority]}\n"
            f"期限: {deadline_str}\n"
            f"ID: #{todo_id}",
        )
        await interaction.followup.send(embed=embed)


class TodoCog(commands.Cog):
    """To-Do管理機能"""

    def __init__(self, bot: commands.Bot, manager: TodoManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.deadline_check.start()

    async def cog_unload(self) -> None:
        self.deadline_check.cancel()

    todo_group = app_commands.Group(name="todo", description="To-Do管理")

    @todo_group.command(name="add", description="タスクを追加（モーダル）")
    async def todo_add_modal(self, interaction: discord.Interaction):
        """モーダルでタスクを追加"""
        await interaction.response.send_modal(TodoModal(self))

    @todo_group.command(name="quick", description="タスクをすばやく追加")
    @app_commands.describe(
        title="タスク名",
        priority="優先度（1=高, 2=中, 3=低）",
        deadline="期限（YYYY-MM-DD HH:MM）",
    )
    async def todo_quick(
        self,
        interaction: discord.Interaction,
        title: str,
        priority: int = 2,
        deadline: str | None = None,
    ):
        if priority not in (1, 2, 3):
            await interaction.response.send_message(
                embed=error_embed("エラー", "優先度は 1, 2, 3 のいずれかです。"),
                ephemeral=True,
            )
            return

        parsed_deadline = None
        if deadline:
            try:
                parsed_deadline = datetime.strptime(deadline.strip(), "%Y-%m-%d %H:%M").replace(
                    tzinfo=UTC
                )
            except ValueError:
                await interaction.response.send_message(
                    embed=error_embed("エラー", "期限の形式: YYYY-MM-DD HH:MM"),
                    ephemeral=True,
                )
                return

        await interaction.response.defer()

        todo_id = await self.manager.add_todo(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id,
            title=title,
            priority=priority,
            deadline=parsed_deadline,
        )

        embed = success_embed("タスク追加", f"**{title}** (#{todo_id})")
        await interaction.followup.send(embed=embed)

    @todo_group.command(name="list", description="タスク一覧を表示")
    @app_commands.describe(status="フィルタ")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="未完了", value="pending"),
            app_commands.Choice(name="完了済み", value="completed"),
            app_commands.Choice(name="全て", value="all"),
        ]
    )
    async def todo_list(
        self,
        interaction: discord.Interaction,
        status: str = "pending",
    ):
        await interaction.response.defer()

        filter_status = None if status == "all" else status
        todos = await self.manager.list_todos(
            interaction.user.id, interaction.guild_id, filter_status
        )

        if not todos:
            await interaction.followup.send(
                embed=info_embed("📋 タスク一覧", "タスクはありません。")
            )
            return

        lines = []
        for todo in todos:
            status_icon = "✅" if todo["status"] == "completed" else "⬜"
            priority_icon = PRIORITY_LABELS.get(todo["priority"], "")
            deadline_str = ""
            if todo.get("deadline"):
                deadline_str = f" (〆{todo['deadline'].strftime('%m/%d')})"

            lines.append(
                f"{status_icon} `#{todo['id']}` {priority_icon} {todo['title']}{deadline_str}"
            )

        embed = info_embed("📋 タスク一覧", "\n".join(lines))
        embed.set_footer(text=f"{len(todos)}件のタスク")
        await interaction.followup.send(embed=embed)

    @todo_group.command(name="complete", description="タスクを完了にする")
    @app_commands.describe(task_id="タスクID")
    async def todo_complete(self, interaction: discord.Interaction, task_id: int):
        await interaction.response.defer()

        todo = await self.manager.complete_todo(task_id, interaction.user.id)
        if not todo:
            await interaction.followup.send(
                embed=error_embed("エラー", "タスクが見つからないか、既に完了しています。"),
                ephemeral=True,
            )
            return

        embed = success_embed("タスク完了！", f"**{todo['title']}** を完了しました🎉")
        await interaction.followup.send(embed=embed)

        # イベント発行: タスク完了
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_todo_complete(
                    user_id=interaction.user.id,
                    guild_id=getattr(interaction, "guild_id", 0) or 0,
                    username=interaction.user.display_name,
                    title=todo["title"],
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

        # XP付与
        gamification = self.bot.get_cog("GamificationCog")
        if gamification:
            try:
                await gamification.award_task_xp(
                    interaction.user.id, todo["priority"], interaction.channel
                )
            except Exception:
                logger.warning("タスク完了のXP付与に失敗", exc_info=True)

    @todo_group.command(name="delete", description="タスクを削除")
    @app_commands.describe(task_id="タスクID")
    async def todo_delete(self, interaction: discord.Interaction, task_id: int):
        deleted = await self.manager.delete_todo(task_id, interaction.user.id)
        if not deleted:
            await interaction.response.send_message(
                embed=error_embed("エラー", "タスクが見つかりません。"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed("削除完了", f"タスク #{task_id} を削除しました。"),
            ephemeral=True,
        )

    @tasks.loop(hours=1)
    async def deadline_check(self):
        """1時間ごとに期限切れタスクをチェック"""
        try:
            for guild in self.bot.guilds:
                upcoming = await self.manager.get_upcoming(guild.id, hours=2)
                for todo in upcoming:
                    user = self.bot.get_user(todo["user_id"])
                    if user:
                        try:
                            embed = discord.Embed(
                                title="⏰ タスク期限アラート",
                                description=(
                                    f"**{todo['title']}** の期限が近づいています！\n"
                                    f"期限: {todo['deadline'].strftime('%Y/%m/%d %H:%M')}"
                                ),
                                color=COLORS["warning"],
                            )
                            embed.set_footer(text="StudyBot タスクリマインダー")
                            await user.send(embed=embed)
                        except discord.Forbidden:
                            pass
        except Exception:
            logger.error("タスク期限チェック中にエラー", exc_info=True)

    @deadline_check.before_loop
    async def before_deadline_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = TodoManager(db_pool)
    await bot.add_cog(TodoCog(bot, manager))
