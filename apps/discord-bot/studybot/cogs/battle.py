"""チームバトル Cog"""

import logging
from datetime import timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS
from studybot.managers.battle_manager import BattleManager
from studybot.utils.embed_helper import error_embed, info_embed

JST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)


class BattleCog(commands.Cog):
    """チームバトル機能"""

    def __init__(self, bot: commands.Bot, manager: BattleManager) -> None:
        self.bot = bot
        self.manager = manager

    async def cog_load(self) -> None:
        self.battle_check.start()

    async def cog_unload(self) -> None:
        self.battle_check.cancel()

    battle_group = app_commands.Group(name="battle", description="チームバトル")

    @battle_group.command(name="challenge", description="チームバトルを開始")
    @app_commands.describe(
        team_b_id="対戦相手チームのID",
        days="バトル期間（日数、デフォルト: 7）",
        goal_type="バトル目標（study_minutes/pomodoro/tasks）",
    )
    async def battle_challenge(
        self,
        interaction: discord.Interaction,
        team_b_id: int,
        days: int = 7,
        goal_type: str = "study_minutes",
    ):
        await interaction.response.defer()

        # Find user's team
        team_cog = self.bot.get_cog("TeamCog")
        if not team_cog:
            await interaction.followup.send(embed=error_embed("エラー", "チーム機能が無効です"))
            return

        user_teams = await team_cog.manager.get_user_teams(interaction.user.id)
        if not user_teams:
            await interaction.followup.send(embed=error_embed("エラー", "チームに所属していません"))
            return

        team_a_id = user_teams[0]["id"]

        result = await self.manager.create_battle(
            guild_id=interaction.guild_id or 0,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            goal_type=goal_type,
            duration_days=days,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("バトル作成失敗", result["error"]))
            return

        goal_labels = {
            "study_minutes": "学習時間（分）",
            "pomodoro": "ポモドーロ回数",
            "tasks": "タスク完了数",
        }

        embed = discord.Embed(
            title="⚔️ チームバトル開始！",
            description=f"**{result['team_a_name']}** vs **{result['team_b_name']}**",
            color=COLORS.get("warning", 0xF59E0B),
        )
        embed.add_field(name="目標", value=goal_labels.get(goal_type, goal_type), inline=True)
        embed.add_field(name="期間", value=f"{days}日間", inline=True)
        embed.add_field(name="バトルID", value=f"#{result['battle_id']}", inline=True)
        embed.set_footer(text="相手チームの /battle accept で開始！")
        await interaction.followup.send(embed=embed)

    @battle_group.command(name="accept", description="バトルを承認")
    @app_commands.describe(battle_id="バトルID")
    async def battle_accept(self, interaction: discord.Interaction, battle_id: int):
        await interaction.response.defer()
        result = await self.manager.accept_battle(battle_id, interaction.user.id)

        if "error" in result:
            await interaction.followup.send(embed=error_embed("承認失敗", result["error"]))
            return

        embed = discord.Embed(
            title="⚔️ バトル開始！",
            description=f"バトル #{battle_id} がアクティブになりました！",
            color=COLORS.get("success", 0x22C55E),
        )
        await interaction.followup.send(embed=embed)

    @battle_group.command(name="status", description="アクティブバトル一覧")
    async def battle_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        battles = await self.manager.battle_repo.get_active_battles(interaction.guild_id or 0)

        if not battles:
            await interaction.followup.send(
                embed=info_embed("チームバトル", "アクティブなバトルはありません")
            )
            return

        embed = discord.Embed(
            title="⚔️ アクティブバトル",
            color=COLORS.get("primary", 0x5865F2),
        )
        for b in battles[:10]:
            status_emoji = "⏳" if b["status"] == "pending" else "⚔️"
            embed.add_field(
                name=f"{status_emoji} #{b['id']} {b['team_a_name']} vs {b['team_b_name']}",
                value=f"スコア: {b['team_a_score']} - {b['team_b_score']} | "
                f"残り: {(b['end_date'] - b['start_date']).days}日",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @battle_group.command(name="detail", description="バトル詳細")
    @app_commands.describe(battle_id="バトルID")
    async def battle_detail(self, interaction: discord.Interaction, battle_id: int):
        await interaction.response.defer()
        detail = await self.manager.get_battle_detail(battle_id)

        if not detail:
            await interaction.followup.send(embed=error_embed("エラー", "バトルが見つかりません"))
            return

        embed = discord.Embed(
            title=f"⚔️ {detail['team_a_name']} vs {detail['team_b_name']}",
            color=COLORS.get("primary", 0x5865F2),
        )
        embed.add_field(
            name=detail["team_a_name"],
            value=f"スコア: **{detail['team_a_score']}**\nメンバー: {detail['team_a_members']}人",
            inline=True,
        )
        embed.add_field(
            name=detail["team_b_name"],
            value=f"スコア: **{detail['team_b_score']}**\nメンバー: {detail['team_b_members']}人",
            inline=True,
        )

        if detail["contributions"]:
            top = detail["contributions"][:5]
            contrib_text = "\n".join(
                f"**{c['username']}** — {c['total_contribution']}" for c in top
            )
            embed.add_field(name="🏆 貢献度ランキング", value=contrib_text, inline=False)

        embed.add_field(name="状態", value=detail["status"], inline=True)
        embed.add_field(
            name="期間",
            value=f"{detail['start_date']} - {detail['end_date']}",
            inline=True,
        )
        await interaction.followup.send(embed=embed)

    @tasks.loop(hours=1)
    async def battle_check(self) -> None:
        """毎時バトル期限チェック"""
        try:
            results = await self.manager.check_battle_completion()
            for r in results:
                logger.info(
                    "バトル #%d 完了 — 勝者チーム: %s",
                    r["battle_id"],
                    r["winner_team_id"],
                )
        except Exception:
            logger.warning("バトルチェック失敗", exc_info=True)

    @battle_check.before_loop
    async def before_battle_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    manager = BattleManager(bot.db_pool)
    await bot.add_cog(BattleCog(bot, manager))
