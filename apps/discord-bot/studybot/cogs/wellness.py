"""ウェルネスチェック Cog"""

import logging

import discord
from discord import TextStyle, app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.wellness_manager import WellnessManager
from studybot.utils.embed_helper import error_embed, wellness_embed

logger = logging.getLogger(__name__)


class WellnessModal(discord.ui.Modal, title="ウェルネスチェック"):
    """ウェルネス入力モーダル"""

    mood = discord.ui.TextInput(
        label="気分 (1-5)",
        placeholder="1=とても悪い, 2=悪い, 3=普通, 4=良い, 5=とても良い",
        max_length=1,
        required=True,
    )
    energy = discord.ui.TextInput(
        label="エネルギー (1-5)",
        placeholder="1=とても低い, 2=低い, 3=普通, 4=高い, 5=とても高い",
        max_length=1,
        required=True,
    )
    stress = discord.ui.TextInput(
        label="ストレス (1-5)",
        placeholder="1=とても低い, 2=低い, 3=普通, 4=高い, 5=とても高い",
        max_length=1,
        required=True,
    )
    note = discord.ui.TextInput(
        label="メモ (任意)",
        style=TextStyle.long,
        required=False,
        max_length=500,
        placeholder="今の気持ちや状態をメモできます",
    )

    def __init__(self, manager: WellnessManager) -> None:
        super().__init__()
        self.manager = manager

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """モーダル送信時の処理"""
        # バリデーション
        try:
            mood_val = int(self.mood.value)
            energy_val = int(self.energy.value)
            stress_val = int(self.stress.value)
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed(
                    "入力エラー", "気分・エネルギー・ストレスは1〜5の数字で入力してください。"
                ),
                ephemeral=True,
            )
            return

        if not (1 <= mood_val <= 5 and 1 <= energy_val <= 5 and 1 <= stress_val <= 5):
            await interaction.response.send_message(
                embed=error_embed("入力エラー", "各値は1〜5の範囲で入力してください。"),
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        result = await self.manager.log_wellness(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            mood=mood_val,
            energy=energy_val,
            stress=stress_val,
            note=self.note.value or "",
        )

        # 結果Embedを構築
        description = (
            f"**気分:** {result['mood_label']}\n"
            f"**エネルギー:** {result['energy_label']}\n"
            f"**ストレス:** {result['stress_label']}\n"
        )

        if self.note.value:
            description += f"\n**メモ:** {self.note.value}\n"

        if result["warning"]:
            description += f"\n⚠️ **アドバイス:** {result['warning']}"

        embed = wellness_embed("ウェルネス記録完了", description)
        embed.set_footer(text=interaction.user.display_name)

        await interaction.followup.send(embed=embed)


class WellnessCog(commands.Cog):
    """ウェルネスチェック機能"""

    def __init__(self, bot: commands.Bot, manager: WellnessManager) -> None:
        self.bot = bot
        self.manager = manager

    wellness_group = app_commands.Group(name="wellness", description="ウェルネス")

    @wellness_group.command(name="check", description="ウェルネスチェックを記録")
    async def wellness_check(self, interaction: discord.Interaction):
        """ウェルネスチェックモーダルを表示"""
        modal = WellnessModal(self.manager)
        await interaction.response.send_modal(modal)

    @wellness_group.command(name="recommend", description="ウェルネスに基づく学習推奨")
    async def wellness_recommend(self, interaction: discord.Interaction):
        """ウェルネスデータに基づいて最適な学習セッションを推奨"""
        await interaction.response.defer(ephemeral=True)

        result = await self.manager.get_recommendation(interaction.user.id)

        if not result["has_data"]:
            await interaction.followup.send(
                embed=wellness_embed("ウェルネス推奨", result["message"]),
                ephemeral=True,
            )
            return

        source_label = "今日の記録" if result["source"] == "today" else "過去7日間の平均"

        embed = discord.Embed(
            title="🧘 ウェルネスベース学習推奨",
            description=f"*{source_label}に基づく推奨です*",
            color=COLORS["wellness"],
        )

        embed.add_field(
            name="現在の状態",
            value=(
                f"気分: {result['mood_label']} ({result['mood']}/5)\n"
                f"エネルギー: {result['energy_label']} ({result['energy']}/5)\n"
                f"ストレス: {result['stress_label']} ({result['stress']}/5)"
            ),
            inline=False,
        )

        embed.add_field(
            name=f"🍅 推奨セッション: {result['session_label']}",
            value=result["advice"],
            inline=False,
        )

        if result["extra_tips"]:
            embed.add_field(
                name="💡 追加アドバイス",
                value="\n".join(result["extra_tips"]),
                inline=False,
            )

        embed.set_footer(
            text=f"/pomodoro start work_min:{result['recommended_minutes']} で開始"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @wellness_group.command(name="stats", description="ウェルネス統計を表示")
    async def wellness_stats(self, interaction: discord.Interaction):
        """ウェルネストレンドチャート + 統計情報を表示"""
        await interaction.response.defer()

        stats = await self.manager.get_stats(interaction.user.id)

        if not stats["has_data"]:
            await interaction.followup.send(
                embed=wellness_embed("ウェルネス統計", stats["message"])
            )
            return

        # 統計Embed
        embed = discord.Embed(
            title="🧘 ウェルネス統計（過去7日間）",
            color=COLORS["wellness"],
        )
        embed.add_field(
            name="平均気分",
            value=f"{stats['avg_mood']:.1f} {stats['mood_label']}",
            inline=True,
        )
        embed.add_field(
            name="平均エネルギー",
            value=f"{stats['avg_energy']:.1f} {stats['energy_label']}",
            inline=True,
        )
        embed.add_field(
            name="平均ストレス",
            value=f"{stats['avg_stress']:.1f} {stats['stress_label']}",
            inline=True,
        )
        embed.add_field(
            name="記録回数",
            value=f"{stats['log_count']}回",
            inline=True,
        )
        embed.set_footer(text=interaction.user.display_name)

        # トレンドチャートを生成
        buf = await self.manager.generate_trend_chart(interaction.user.id)

        if buf:
            file = discord.File(buf, filename="wellness_trend.png")
            embed.set_image(url="attachment://wellness_trend.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = WellnessManager(db_pool)
    await bot.add_cog(WellnessCog(bot, manager))
