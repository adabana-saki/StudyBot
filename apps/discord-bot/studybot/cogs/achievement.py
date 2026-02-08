"""実績システム Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.managers.achievement_manager import AchievementManager
from studybot.utils.embed_helper import achievement_embed

logger = logging.getLogger(__name__)


def _progress_bar(current: int, target: int, width: int = 10) -> str:
    """実績進捗バー"""
    ratio = min(1.0, current / target) if target > 0 else 0
    filled = int(width * ratio)
    bar = "▓" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{target}"


class AchievementCog(commands.Cog):
    """実績システム機能"""

    def __init__(self, bot: commands.Bot, manager: AchievementManager) -> None:
        self.bot = bot
        self.manager = manager

    achievement_group = app_commands.Group(name="achievements", description="実績")

    @achievement_group.command(name="list", description="全実績の一覧を表示")
    async def achievement_list(self, interaction: discord.Interaction):
        await interaction.response.defer()

        achievements = await self.manager.get_all_with_progress(interaction.user.id)

        if not achievements:
            await interaction.followup.send(
                embed=achievement_embed("実績一覧", "実績がまだ登録されていません。")
            )
            return

        # カテゴリごとにグループ化
        categories: dict[str, list] = {}
        for ach in achievements:
            cat = ach["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(ach)

        category_labels = {
            "study": "📖 学習",
            "streak": "🔥 連続学習",
            "raid": "⚔️ レイド",
            "tasks": "✅ タスク",
            "general": "🏅 一般",
        }

        embed = achievement_embed("実績一覧", "")
        for cat, achs in categories.items():
            lines = []
            for ach in achs:
                if ach["unlocked"]:
                    status = "✅"
                else:
                    status = _progress_bar(ach["progress"], ach["target_value"])

                lines.append(f"{ach['emoji']} **{ach['name']}** {status}\n　_{ach['description']}_")

            cat_label = category_labels.get(cat, cat)
            embed.add_field(
                name=cat_label,
                value="\n".join(lines),
                inline=False,
            )

        # アンロック済み数
        unlocked = sum(1 for a in achievements if a["unlocked"])
        embed.set_footer(text=f"解放済み: {unlocked}/{len(achievements)}")

        await interaction.followup.send(embed=embed)

    @achievement_group.command(name="progress", description="自分の実績進捗を表示")
    async def achievement_progress(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        unlocked = await self.manager.get_user_unlocked(interaction.user.id)

        if not unlocked:
            await interaction.followup.send(
                embed=achievement_embed(
                    "実績進捗",
                    "まだ実績を解放していません。\n学習を続けて実績を解放しましょう！",
                ),
                ephemeral=True,
            )
            return

        lines = []
        total_coins = 0
        for ach in unlocked:
            unlock_date = ""
            if ach.get("unlocked_at"):
                unlock_date = f" ({ach['unlocked_at'].strftime('%Y/%m/%d')})"
            lines.append(f"{ach['emoji']} **{ach['name']}**{unlock_date}")
            total_coins += ach.get("reward_coins", 0)

        embed = achievement_embed(
            f"{interaction.user.display_name} の実績",
            "\n".join(lines),
        )
        embed.add_field(
            name="獲得報酬",
            value=f"🪙 {total_coins:,} StudyCoin",
            inline=False,
        )
        embed.set_footer(text=f"解放済み: {len(unlocked)}件")
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def check_achievement(
        self,
        user_id: int,
        key: str,
        value: int,
        channel: discord.abc.Messageable | None = None,
    ) -> None:
        """実績チェック（他Cogから呼び出し）"""
        result = await self.manager.check_and_update(user_id, key, value)

        if result and result.get("unlocked") and channel:
            ach = result["achievement"]
            embed = achievement_embed(
                "実績解放！",
                f"{ach['emoji']} **{ach['name']}**\n_{ach['description']}_",
            )

            # コイン報酬
            reward_coins = result.get("reward_coins", 0)
            if reward_coins > 0:
                embed.add_field(
                    name="報酬",
                    value=f"🪙 {reward_coins:,} StudyCoin",
                    inline=False,
                )

                # コイン付与
                shop_cog = self.bot.get_cog("ShopCog")
                if shop_cog:
                    await shop_cog.award_coins(
                        user_id, "", reward_coins, f"実績解放: {ach['name']}"
                    )

            await channel.send(f"<@{user_id}>", embed=embed)

            # イベント発行: 実績解放
            if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
                try:
                    await self.bot.event_publisher.emit_achievement_unlock(
                        user_id=user_id,
                        guild_id=0,
                        username="",
                        achievement_name=ach.get("name", ""),
                        achievement_emoji=ach.get("emoji", ""),
                    )
                except Exception:
                    logger.warning("イベント発行失敗", exc_info=True)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = AchievementManager(db_pool)
    await bot.add_cog(AchievementCog(bot, manager))
