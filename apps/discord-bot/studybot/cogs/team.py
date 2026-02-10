"""スタディチーム Cog"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.team_manager import TeamManager
from studybot.utils.embed_helper import error_embed, team_embed

logger = logging.getLogger(__name__)


class TeamCog(commands.Cog):
    """スタディチーム機能"""

    def __init__(self, bot: commands.Bot, manager: TeamManager) -> None:
        self.bot = bot
        self.manager = manager

    team_group = app_commands.Group(name="team", description="スタディチーム")

    @team_group.command(name="create", description="チームを作成")
    @app_commands.describe(
        name="チーム名",
        max_members="最大メンバー数（デフォルト: 10）",
    )
    async def team_create(
        self,
        interaction: discord.Interaction,
        name: str,
        max_members: int = 10,
    ):
        await interaction.response.defer()
        result = await self.manager.create_team(
            creator_id=interaction.user.id,
            username=interaction.user.display_name,
            guild_id=interaction.guild_id or 0,
            name=name,
            max_members=max_members,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("チーム作成", result["error"]))
            return

        embed = discord.Embed(
            title="チーム作成完了！",
            description=f"**{result['name']}**",
            color=COLORS["team"],
        )
        embed.add_field(name="チームID", value=f"#{result['team_id']}", inline=True)
        embed.add_field(name="最大人数", value=f"{result['max_members']}人", inline=True)
        embed.set_footer(text="/team join で参加しよう！")
        await interaction.followup.send(embed=embed)

    @team_group.command(name="join", description="チームに参加")
    @app_commands.describe(team_id="チームID")
    async def team_join(self, interaction: discord.Interaction, team_id: int):
        await interaction.response.defer()
        result = await self.manager.join_team(
            team_id=team_id,
            user_id=interaction.user.id,
            username=interaction.user.display_name,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("チーム参加", result["error"]))
            return

        embed = team_embed(
            "チーム参加",
            f"**{result['name']}** に参加しました！\nメンバー数: {result['member_count']}人",
        )
        await interaction.followup.send(embed=embed)

    @team_group.command(name="leave", description="チームから脱退")
    @app_commands.describe(team_id="チームID")
    async def team_leave(self, interaction: discord.Interaction, team_id: int):
        await interaction.response.defer()
        result = await self.manager.leave_team(
            team_id=team_id,
            user_id=interaction.user.id,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("チーム脱退", result["error"]))
            return

        embed = team_embed(
            "チーム脱退",
            f"**{result['name']}** から脱退しました。",
        )
        await interaction.followup.send(embed=embed)

    @team_group.command(name="list", description="サーバーのチーム一覧")
    async def team_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        teams = await self.manager.list_guild_teams(interaction.guild_id or 0)

        if not teams:
            embed = team_embed(
                "チーム一覧",
                "まだチームがありません。\n`/team create` で作成しましょう！",
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(title="スタディチーム一覧", color=COLORS["team"])
        for t in teams[:10]:
            embed.add_field(
                name=f"#{t['id']} {t['name']}",
                value=(
                    f"メンバー: {t['member_count']}/{t['max_members']}人\n"
                    f"作成者: <@{t['creator_id']}>"
                ),
                inline=True,
            )
        await interaction.followup.send(embed=embed)

    @team_group.command(name="stats", description="チーム統計を表示")
    @app_commands.describe(team_id="チームID")
    async def team_stats(self, interaction: discord.Interaction, team_id: int):
        await interaction.response.defer()
        result = await self.manager.get_team_stats(team_id)

        if not result:
            await interaction.followup.send(
                embed=error_embed("チーム統計", "チームが見つかりません")
            )
            return

        team = result["team"]
        stats = result["stats"]
        weekly = result["weekly"]

        embed = discord.Embed(
            title=f"{team['name']} の統計",
            color=COLORS["team"],
        )
        embed.add_field(
            name="メンバー数",
            value=f"{team['member_count']}/{team['max_members']}人",
            inline=True,
        )

        # 累計統計
        hours = stats["total_minutes"] // 60
        mins = stats["total_minutes"] % 60
        embed.add_field(
            name="累計学習時間",
            value=f"{hours}時間{mins}分",
            inline=True,
        )
        embed.add_field(
            name="累計セッション数",
            value=f"{stats['total_sessions']}回",
            inline=True,
        )
        embed.add_field(
            name="メンバー平均",
            value=f"{stats['avg_minutes_per_member']}分",
            inline=True,
        )

        # 週次統計
        w_hours = weekly["weekly_minutes"] // 60
        w_mins = weekly["weekly_minutes"] % 60
        embed.add_field(
            name="今週の学習時間",
            value=f"{w_hours}時間{w_mins}分",
            inline=True,
        )
        embed.add_field(
            name="今週のセッション",
            value=f"{weekly['weekly_sessions']}回",
            inline=True,
        )

        await interaction.followup.send(embed=embed)

    @team_group.command(name="quest", description="チームクエストを表示")
    @app_commands.describe(team_id="チームID")
    async def team_quest(self, interaction: discord.Interaction, team_id: int):
        await interaction.response.defer()

        team = await self.manager.repository.get_team(team_id)
        if not team:
            await interaction.followup.send(
                embed=error_embed("チームクエスト", "チームが見つかりません")
            )
            return

        quests = await self.manager.get_team_quests(team_id)

        embed = discord.Embed(
            title=f"📋 {team['name']} のチームクエスト",
            description="チームメンバー全員の活動で進捗します",
            color=COLORS["team"],
        )

        for q in quests:
            qt = q.get("quest_type", "")
            label = self.manager.get_team_quest_label(qt)
            unit = self.manager.get_team_quest_unit(qt)
            target = q.get("target", 0)
            progress = q.get("progress", 0)
            completed = q.get("completed", False)
            claimed = q.get("claimed", False)

            if claimed:
                status = "🎁 受取済"
            elif completed:
                status = "✅ 完了（/team quest_claim で受取）"
            else:
                pct = int(progress / target * 100) if target > 0 else 0
                filled = int(10 * min(1.0, pct / 100))
                bar = "\u2588" * filled + "\u2591" * (10 - filled)
                status = f"[{bar}] {progress}/{target}{unit}"

            quest_id = q.get("id", "?")
            embed.add_field(
                name=f"#{quest_id} {label} ({target}{unit})",
                value=(
                    f"{status}\n報酬: {q.get('reward_xp', 0)} XP + {q.get('reward_coins', 0)} 🪙"
                ),
                inline=False,
            )

        embed.set_footer(text="チームメンバーの学習が自動で反映されます")
        await interaction.followup.send(embed=embed)

    @team_group.command(name="quest_claim", description="チームクエスト報酬を受け取る")
    @app_commands.describe(team_id="チームID", quest_id="クエストID")
    async def team_quest_claim(self, interaction: discord.Interaction, team_id: int, quest_id: int):
        await interaction.response.defer()
        result = await self.manager.claim_team_quest(team_id, quest_id)

        if "error" in result:
            await interaction.followup.send(
                embed=error_embed("チームクエスト報酬", result["error"])
            )
            return

        label = self.manager.get_team_quest_label(result["quest_type"])
        embed = team_embed(
            "チームクエスト報酬受取",
            (
                f"**{label}** の報酬を受け取りました！\n\n"
                f"**+{result['reward_xp']} XP**\n"
                f"**+{result['reward_coins']} 🪙 StudyCoin**\n\n"
                "チーム全員に反映されます"
            ),
        )
        await interaction.followup.send(embed=embed)

    @team_group.command(name="members", description="チームメンバーを表示")
    @app_commands.describe(team_id="チームID")
    async def team_members(self, interaction: discord.Interaction, team_id: int):
        await interaction.response.defer()
        result = await self.manager.get_team_members(team_id)

        if "error" in result:
            await interaction.followup.send(embed=error_embed("チームメンバー", result["error"]))
            return

        team = result["team"]
        members = result["members"]

        embed = discord.Embed(
            title=f"{team['name']} のメンバー",
            description=f"メンバー数: {len(members)}/{team['max_members']}人",
            color=COLORS["team"],
        )
        for i, m in enumerate(members):
            is_creator = m["user_id"] == team["creator_id"]
            role = " (リーダー)" if is_creator else ""
            embed.add_field(
                name=f"{i + 1}. {m['username']}{role}",
                value=f"<@{m['user_id']}>",
                inline=True,
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = TeamManager(db_pool)
    await bot.add_cog(TeamCog(bot, manager))
