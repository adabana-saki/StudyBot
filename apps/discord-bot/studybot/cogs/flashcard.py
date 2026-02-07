"""フラッシュカード Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.flashcard_manager import FlashcardManager
from studybot.utils.embed_helper import error_embed, study_embed, success_embed

logger = logging.getLogger(__name__)

# 評価ラベル
QUALITY_LABELS = {
    1: "全く覚えていない",
    2: "ほぼ忘れた",
    3: "難しかった",
    4: "良い",
    5: "完璧",
}


class FlashcardRevealView(discord.ui.View):
    """カードの裏面を表示するビュー"""

    def __init__(
        self,
        manager: FlashcardManager,
        user_id: int,
        cards: list[dict],
        current_index: int,
        results: list[dict],
    ) -> None:
        super().__init__(timeout=300)
        self.manager = manager
        self.user_id = user_id
        self.cards = cards
        self.current_index = current_index
        self.results = results

    @discord.ui.button(label="答えを見る", style=discord.ButtonStyle.primary, emoji="👁️")
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "このセッションは他のユーザーのものです。", ephemeral=True
            )
            return

        card = self.cards[self.current_index]
        embed = discord.Embed(
            title=f"🃏 カード {self.current_index + 1}/{len(self.cards)}",
            color=COLORS["study"],
        )
        embed.add_field(name="表", value=card["front"], inline=False)
        embed.add_field(name="裏", value=card["back"], inline=False)
        embed.set_footer(text="覚え具合を評価してください")

        view = FlashcardRatingView(
            manager=self.manager,
            user_id=self.user_id,
            cards=self.cards,
            current_index=self.current_index,
            card=card,
            results=self.results,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class FlashcardRatingView(discord.ui.View):
    """評価ボタンを表示するビュー"""

    def __init__(
        self,
        manager: FlashcardManager,
        user_id: int,
        cards: list[dict],
        current_index: int,
        card: dict,
        results: list[dict],
    ) -> None:
        super().__init__(timeout=300)
        self.manager = manager
        self.user_id = user_id
        self.cards = cards
        self.current_index = current_index
        self.card = card
        self.results = results

        # 評価ボタンを動的に追加
        for quality, label in QUALITY_LABELS.items():
            button = discord.ui.Button(
                label=f"{quality}: {label}",
                style=self._get_button_style(quality),
                custom_id=f"rate_{quality}",
            )
            button.callback = self._make_callback(quality)
            self.add_item(button)

    @staticmethod
    def _get_button_style(quality: int) -> discord.ButtonStyle:
        if quality <= 2:
            return discord.ButtonStyle.danger
        elif quality == 3:
            return discord.ButtonStyle.secondary
        else:
            return discord.ButtonStyle.success

    def _make_callback(self, quality: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message(
                    "このセッションは他のユーザーのものです。", ephemeral=True
                )
                return

            # SM-2アルゴリズムを適用
            result = await self.manager.review_card_with_state(
                card_id=self.card["id"],
                user_id=self.user_id,
                quality=quality,
                easiness=self.card.get("easiness", 2.5),
                interval=self.card.get("interval", 0),
                repetitions=self.card.get("repetitions", 0),
            )

            self.results.append(
                {
                    "front": self.card["front"],
                    "quality": quality,
                    "interval": result["interval"],
                }
            )

            next_index = self.current_index + 1

            if next_index < len(self.cards):
                # 次のカードを表示
                next_card = self.cards[next_index]
                embed = discord.Embed(
                    title=f"🃏 カード {next_index + 1}/{len(self.cards)}",
                    description=next_card["front"],
                    color=COLORS["study"],
                )
                embed.set_footer(text="「答えを見る」ボタンで裏面を確認")

                view = FlashcardRevealView(
                    manager=self.manager,
                    user_id=self.user_id,
                    cards=self.cards,
                    current_index=next_index,
                    results=self.results,
                )
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                # セッション完了
                summary_lines = []
                for r in self.results:
                    label = QUALITY_LABELS.get(r["quality"], "?")
                    summary_lines.append(f"• {r['front']} → {label} (次回: {r['interval']}日後)")

                embed = discord.Embed(
                    title="🎉 セッション完了！",
                    description="\n".join(summary_lines),
                    color=COLORS["success"],
                )
                embed.set_footer(text=f"{len(self.results)}枚のカードを復習しました")
                await interaction.response.edit_message(embed=embed, view=None)

        return callback


class FlashcardCog(commands.Cog):
    """フラッシュカード機能"""

    def __init__(self, bot: commands.Bot, manager: FlashcardManager) -> None:
        self.bot = bot
        self.manager = manager

    flashcard_group = app_commands.Group(name="flashcard", description="フラッシュカード")

    @flashcard_group.command(name="create", description="フラッシュカードを作成")
    @app_commands.describe(
        topic="デッキ名（トピック）",
        front="カードの表面（問題）",
        back="カードの裏面（答え）",
    )
    async def flashcard_create(
        self,
        interaction: discord.Interaction,
        topic: str,
        front: str,
        back: str,
    ):
        await interaction.response.defer()

        result = await self.manager.add_card(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            deck_name=topic,
            front=front,
            back=back,
        )

        card = result["card"]
        deck = result["deck"]
        embed = success_embed(
            "カード追加完了",
            f"デッキ: **{deck['name']}**\n"
            f"表: {card['front']}\n"
            f"裏: {card['back']}\n"
            f"カード数: {deck.get('card_count', 0) + 1}",
        )
        await interaction.followup.send(embed=embed)

    @flashcard_group.command(name="study", description="フラッシュカードで学習開始")
    @app_commands.describe(topic="デッキ名（トピック）")
    async def flashcard_study(self, interaction: discord.Interaction, topic: str):
        await interaction.response.defer()

        result = await self.manager.get_review_cards(
            user_id=interaction.user.id,
            deck_name=topic,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("エラー", result["error"]))
            return

        cards = result["cards"]
        deck = result["deck"]

        if not cards:
            await interaction.followup.send(
                embed=study_embed(
                    f"📚 {deck['name']}",
                    result.get("message", "復習するカードはありません。"),
                )
            )
            return

        # 最初のカードを表示
        first_card = cards[0]
        embed = discord.Embed(
            title=f"🃏 カード 1/{len(cards)}",
            description=first_card["front"],
            color=COLORS["study"],
        )
        embed.set_footer(text="「答えを見る」ボタンで裏面を確認")

        view = FlashcardRevealView(
            manager=self.manager,
            user_id=interaction.user.id,
            cards=cards,
            current_index=0,
            results=[],
        )
        await interaction.followup.send(embed=embed, view=view)

    @flashcard_group.command(name="stats", description="フラッシュカードの統計を表示")
    async def flashcard_stats(self, interaction: discord.Interaction):
        await interaction.response.defer()

        stats_list = await self.manager.get_user_stats(interaction.user.id)

        if not stats_list:
            await interaction.followup.send(
                embed=study_embed("📊 フラッシュカード統計", "デッキがありません。")
            )
            return

        lines = []
        for item in stats_list:
            deck = item["deck"]
            stats = item["stats"]
            total = stats["total"]
            mastered = stats["mastered"]
            learning = stats["learning"]
            new = stats["new"]

            mastery_pct = round(mastered / total * 100) if total > 0 else 0
            bar_filled = mastery_pct // 10
            bar_empty = 10 - bar_filled
            bar = "█" * bar_filled + "░" * bar_empty

            lines.append(
                f"**{deck['name']}** ({total}枚)\n"
                f"  {bar} {mastery_pct}%\n"
                f"  習得: {mastered} | 学習中: {learning} | 新規: {new}"
            )

        embed = discord.Embed(
            title="📊 フラッシュカード統計",
            description="\n\n".join(lines),
            color=COLORS["study"],
        )
        embed.set_footer(text=interaction.user.display_name)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = FlashcardManager(db_pool)
    await bot.add_cog(FlashcardCog(bot, manager))
