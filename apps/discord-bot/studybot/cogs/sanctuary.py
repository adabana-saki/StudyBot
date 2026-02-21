"""サンクチュアリ Cog - 癒しの学習庭園"""

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS
from studybot.managers.sanctuary_manager import (
    PHASES,
    PLANT_TYPES,
    SanctuaryManager,
)
from studybot.utils.embed_helper import error_embed, success_embed

logger = logging.getLogger(__name__)


class SessionStartModal(discord.ui.Modal, title="セッション開始"):
    """セッション開始時のムード入力"""

    mood = discord.ui.TextInput(
        label="現在のムード (1-5)",
        placeholder="1=とても悪い, 3=普通, 5=とても良い",
        max_length=1,
        required=True,
    )
    energy = discord.ui.TextInput(
        label="現在のエネルギー (1-5)",
        placeholder="1=とても低い, 3=普通, 5=とても高い",
        max_length=1,
        required=True,
    )

    def __init__(self, cog: "SanctuaryCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            mood = int(self.mood.value)
            energy = int(self.energy.value)
            if not (1 <= mood <= 5 and 1 <= energy <= 5):
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed("入力エラー", "1-5の数値を入力してください"),
                ephemeral=True,
            )
            return

        session = await self.cog.manager.start_session(interaction.user.id, mood, energy)
        if not session:
            await interaction.response.send_message(
                embed=error_embed("エラー", "既にアクティブなセッションがあります"),
                ephemeral=True,
            )
            return

        phase_info = PHASES.get(session["phase"], {})
        phase_name = phase_info.get("name", session["phase"])
        phase_emoji = phase_info.get("emoji", "")
        embed = discord.Embed(
            title="🌿 サンクチュアリセッション開始",
            description=(
                f"フェーズ: {phase_emoji} {phase_name}\n"
                f"ムード: {'😊' * mood}\n"
                f"エネルギー: {'⚡' * energy}\n\n"
                "学習を終えたら `/sanctuary reflect` で振り返りましょう"
            ),
            color=COLORS["sanctuary"],
        )
        await interaction.response.send_message(embed=embed)


class SessionReflectModal(discord.ui.Modal, title="セッション振り返り"):
    """セッション完了時の振り返り"""

    mood = discord.ui.TextInput(
        label="現在のムード (1-5)",
        placeholder="1=とても悪い, 3=普通, 5=とても良い",
        max_length=1,
        required=True,
    )
    energy = discord.ui.TextInput(
        label="現在のエネルギー (1-5)",
        placeholder="1=とても低い, 3=普通, 5=とても高い",
        max_length=1,
        required=True,
    )
    duration = discord.ui.TextInput(
        label="学習時間（分）",
        placeholder="例: 30",
        max_length=3,
        required=True,
    )
    note = discord.ui.TextInput(
        label="メモ（任意）",
        style=discord.TextStyle.paragraph,
        placeholder="学んだことや気づきを書いてみましょう",
        required=False,
        max_length=500,
    )

    def __init__(self, cog: "SanctuaryCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            mood = int(self.mood.value)
            energy = int(self.energy.value)
            duration = int(self.duration.value)
            if not (1 <= mood <= 5 and 1 <= energy <= 5):
                raise ValueError
            if duration <= 0 or duration > 720:
                await interaction.response.send_message(
                    embed=error_embed("エラー", "学習時間は1-720分で入力してください"),
                    ephemeral=True,
                )
                return
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed("入力エラー", "正しい数値を入力してください"),
                ephemeral=True,
            )
            return

        result = await self.cog.manager.complete_session(
            interaction.user.id, mood, energy, duration, self.note.value or ""
        )
        if not result:
            await interaction.response.send_message(
                embed=error_embed("エラー", "アクティブなセッションがありません"),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🌿 セッション完了！",
            description=f"成長ポイント: **+{result['growth_points']:.1f}**",
            color=COLORS["sanctuary"],
        )
        embed.add_field(name="学習時間", value=f"{duration}分", inline=True)
        mood_before = result["session"]["mood_before"]
        embed.add_field(name="ムード変化", value=f"{mood_before} → {mood}", inline=True)

        if result["grown_plants"]:
            plant_text = ""
            for p in result["grown_plants"]:
                stage = p["stage"]
                evolved = " **進化！**" if p["evolved"] else ""
                plant_text += f"{stage['emoji']} {p['name']} ({p['growth']:.0f}%){evolved}\n"
            embed.add_field(name="植物の成長", value=plant_text, inline=False)

        await interaction.response.send_message(embed=embed)


class SanctuaryCog(commands.Cog):
    """サンクチュアリ - 癒しの学習庭園"""

    def __init__(self, bot: commands.Bot, manager: SanctuaryManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.garden_daily_update.start()

    async def cog_unload(self) -> None:
        self.garden_daily_update.cancel()

    @tasks.loop(hours=24)
    async def garden_daily_update(self) -> None:
        """毎日の庭園更新: 植物健康度減衰"""
        try:
            result = await self.manager.daily_update()
            logger.info("庭園日次更新完了: %s", result)
        except Exception:
            logger.error("庭園日次更新失敗", exc_info=True)

    @garden_daily_update.before_loop
    async def before_garden_update(self) -> None:
        await self.bot.wait_until_ready()

    # --- 外部連携メソッド ---

    async def award_growth_points(self, user_id: int, minutes: int) -> None:
        """gamificationフック: 学習による庭園成長"""
        try:
            await self.manager.award_growth_from_study(user_id, minutes)
        except Exception:
            logger.debug("庭園成長付与失敗 (user=%d)", user_id, exc_info=True)

    # --- コマンド ---

    sanctuary_group = app_commands.Group(
        name="sanctuary", description="サンクチュアリ - 癒しの学習庭園"
    )

    @sanctuary_group.command(name="garden", description="庭園を表示")
    async def garden(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        view = await self.manager.get_garden_view(interaction.user.id)
        garden = view["garden"]
        plants = view["plants"]
        phase = view["phase"]
        phase_info = PHASES.get(phase, {})

        embed = discord.Embed(
            title=f"🌿 {interaction.user.display_name}の庭園",
            description=(
                f"フェーズ: {phase_info.get('emoji', '')} {phase_info.get('name', phase)}\n"
                f"活力: {garden.get('vitality', 0):.0f}%  |  調和: {garden.get('harmony', 0):.0f}%"
            ),
            color=COLORS["sanctuary"],
        )

        if plants:
            grid = ""
            for p in plants:
                stage = p["stage"]
                ptype = PLANT_TYPES.get(p["plant_type"], {})
                health_bar = "🟢" if p["health"] > 50 else "🟡" if p["health"] > 20 else "🔴"
                grid += (
                    f"{stage['emoji']} **{p['name']}** "
                    f"({ptype.get('emoji', '🌱')} {stage['name']}) "
                    f"{health_bar} {p['health']:.0f}% | 成長 {p['growth']:.0f}%\n"
                )
            embed.add_field(name=f"植物 ({len(plants)})", value=grid, inline=False)
        else:
            embed.add_field(
                name="植物",
                value="まだ植物がありません。`/sanctuary plant` で種を植えましょう！",
                inline=False,
            )

        stats = view["stats"]
        if stats.get("total_sessions", 0) > 0:
            embed.add_field(
                name="統計",
                value=(
                    f"セッション数: {stats['total_sessions']}\n"
                    f"総成長: {float(stats.get('total_growth', 0)):.0f}pt\n"
                    f"平均ムード変化: {float(stats.get('avg_mood_change', 0)):+.1f}"
                ),
                inline=True,
            )

        embed.set_footer(text="競争要素ゼロ - あなただけの庭園です")
        await interaction.followup.send(embed=embed)

    @sanctuary_group.command(name="plant", description="新しい種を植える")
    @app_commands.describe(
        plant_type="植物の種類",
        name="植物の名前（任意）",
    )
    @app_commands.choices(
        plant_type=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in PLANT_TYPES.items()
        ]
    )
    async def plant(
        self,
        interaction: discord.Interaction,
        plant_type: str,
        name: str = "",
    ) -> None:
        result = await self.manager.plant_seed(interaction.user.id, plant_type, name)
        if not result:
            info = PLANT_TYPES.get(plant_type)
            if not info:
                msg = "不明な植物タイプです"
            else:
                msg = "庭園がいっぱいです（最大12本）"
            await interaction.response.send_message(
                embed=error_embed("植え付け失敗", msg), ephemeral=True
            )
            return

        ptype = PLANT_TYPES[plant_type]
        embed = discord.Embed(
            title=f"{ptype['emoji']} 種を植えました！",
            description=(
                f"**{result['name']}** ({ptype['name']})\n"
                f"{ptype['description']}\n\n"
                "学習を続けて育てましょう！"
            ),
            color=COLORS["sanctuary"],
        )
        await interaction.response.send_message(embed=embed)

    @sanctuary_group.command(name="tend", description="庭の手入れ")
    async def tend(self, interaction: discord.Interaction) -> None:
        result = await self.manager.tend_garden(interaction.user.id)

        if result["count"] == 0:
            await interaction.response.send_message(
                embed=success_embed("手入れ完了", "すべての植物が元気です！"),
                ephemeral=True,
            )
            return

        desc = ""
        for p in result["tended"]:
            ptype = PLANT_TYPES.get(p["type"], {})
            desc += (
                f"{ptype.get('emoji', '🌱')} **{p['name']}**: "
                f"健康度 {p['health_before']:.0f}% → {p['health_after']:.0f}%\n"
            )

        embed = discord.Embed(
            title="🌿 庭の手入れ完了",
            description=desc,
            color=COLORS["sanctuary"],
        )
        await interaction.response.send_message(embed=embed)

    @sanctuary_group.command(name="session", description="サンクチュアリセッション開始")
    async def session(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(SessionStartModal(self))

    @sanctuary_group.command(name="reflect", description="セッション完了 & 振り返り")
    async def reflect(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(SessionReflectModal(self))

    @sanctuary_group.command(name="stats", description="セルフケア分析")
    async def stats(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        data = await self.manager.get_stats(interaction.user.id)
        stats = data["stats"]

        embed = discord.Embed(
            title="🌿 セルフケア分析",
            description="あなた専用のウェルネスメトリクス",
            color=COLORS["sanctuary"],
        )
        embed.add_field(
            name="庭園",
            value=(f"植物数: {data['plant_count']}\n健康な植物: {data['healthy_plants']}"),
            inline=True,
        )
        embed.add_field(
            name="セッション",
            value=(
                f"総セッション: {stats.get('total_sessions', 0)}\n"
                f"総成長ポイント: {float(stats.get('total_growth', 0)):.0f}\n"
                f"平均成長: {float(stats.get('avg_growth', 0)):.1f}/回"
            ),
            inline=True,
        )
        embed.set_footer(text="全メトリクスはあなた専用です")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    manager = SanctuaryManager(bot.db_pool)
    await bot.add_cog(SanctuaryCog(bot, manager))
