"""デイリークエスト Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.quest_manager import QuestManager
from studybot.utils.embed_helper import error_embed, success_embed

logger = logging.getLogger(__name__)


class QuestCog(commands.Cog):
    """デイリークエスト機能"""

    def __init__(self, bot: commands.Bot, manager: QuestManager) -> None:
        self.bot = bot
        self.manager = manager

    quest_group = app_commands.Group(name="quest", description="デイリークエスト")

    @quest_group.command(name="daily", description="今日のデイリークエストを表示")
    async def quest_daily(self, interaction: discord.Interaction):
        await interaction.response.defer()
        quests = await self.manager.get_daily_quests(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
        )

        embed = discord.Embed(
            title="📋 今日のデイリークエスト",
            description="毎日0時(JST)にリセットされます",
            color=COLORS["quest"],
        )

        for i, q in enumerate(quests, 1):
            quest_type = q.get("quest_type", "")
            label = self.manager.get_quest_label(quest_type)
            unit = self.manager.get_quest_unit(quest_type)
            target = q.get("target", 0)
            progress = q.get("progress", 0)
            completed = q.get("completed", False)
            claimed = q.get("claimed", False)

            # ステータスアイコン
            if claimed:
                status = "🎁 受取済"
            elif completed:
                status = "✅ 完了（/quest claim で受取）"
            else:
                pct = int(progress / target * 100) if target > 0 else 0
                filled = int(10 * min(1.0, pct / 100))
                bar = "\u2588" * filled + "\u2591" * (10 - filled)
                status = f"[{bar}] {progress}/{target}{unit}"

            quest_id = q.get("id", "?")
            reward_xp = q.get("reward_xp", 0)
            reward_coins = q.get("reward_coins", 0)
            embed.add_field(
                name=f"#{quest_id} {label} ({target}{unit})",
                value=(
                    f"{status}\n"
                    f"報酬: {reward_xp} XP + {reward_coins} 🪙"
                ),
                inline=False,
            )

        embed.set_footer(text="クエスト完了後、/quest claim <ID> で報酬を受け取れます")
        await interaction.followup.send(embed=embed)

    @quest_group.command(name="claim", description="完了したクエストの報酬を受け取る")
    @app_commands.describe(quest_id="クエストID")
    async def quest_claim(self, interaction: discord.Interaction, quest_id: int):
        await interaction.response.defer()
        result = await self.manager.claim_quest(
            user_id=interaction.user.id,
            quest_id=quest_id,
        )

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("クエスト報酬", result["error"])
            )
            return

        label = self.manager.get_quest_label(result["quest_type"])
        embed = success_embed(
            "クエスト報酬受取",
            (
                f"**{label}** の報酬を受け取りました！\n\n"
                f"**+{result['reward_xp']} XP**\n"
                f"**+{result['reward_coins']} 🪙 StudyCoin**"
            ),
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = QuestManager(db_pool)
    await bot.add_cog(QuestCog(bot, manager))
