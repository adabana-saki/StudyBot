"""リーダーボード Cog"""

import logging
from datetime import time, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COLORS, MEDAL_EMOJIS, PERIOD_LABELS
from studybot.repositories.gamification_repository import GamificationRepository
from studybot.repositories.study_repository import StudyRepository
from studybot.repositories.todo_repository import TodoRepository

JST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)

PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30, "all_time": 3650}


class LeaderboardView(discord.ui.View):
    """ページネーション付きリーダーボード"""

    def __init__(
        self,
        entries: list[dict],
        title: str,
        user_id: int,
        user_rank: int,
        page_size: int = 10,
    ) -> None:
        super().__init__(timeout=120)
        self.entries = entries
        self.title = title
        self.user_id = user_id
        self.user_rank = user_rank
        self.page_size = page_size
        self.page = 0
        self.max_page = max(0, (len(entries) - 1) // page_size)

    def build_embed(self) -> discord.Embed:
        start = self.page * self.page_size
        end = start + self.page_size
        page_entries = self.entries[start:end]

        lines = []
        for i, entry in enumerate(page_entries):
            rank = start + i + 1
            medal = MEDAL_EMOJIS[rank - 1] if rank <= 3 else f"`{rank}.`"
            name = entry.get("username", "Unknown")
            value = entry.get("display_value", "")
            lines.append(f"{medal} **{name}** - {value}")

        description = "\n".join(lines) if lines else "データがありません。"

        if self.user_rank > 0:
            description += f"\n\n📍 あなたの順位: **#{self.user_rank}**"

        embed = discord.Embed(
            title=self.title,
            description=description,
            color=COLORS["xp"],
        )

        if self.max_page > 0:
            embed.set_footer(text=f"ページ {self.page + 1}/{self.max_page + 1}")

        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class LeaderboardCog(commands.Cog):
    """リーダーボード機能"""

    def __init__(self, bot: commands.Bot, db_pool) -> None:
        self.bot = bot
        self.db_pool = db_pool
        self.study_repo = StudyRepository(db_pool)
        self.gamification_repo = GamificationRepository(db_pool)
        self.todo_repo = TodoRepository(db_pool)

    async def cog_load(self) -> None:
        self.daily_leaderboard_post.start()

    async def cog_unload(self) -> None:
        self.daily_leaderboard_post.cancel()

    @app_commands.command(name="leaderboard", description="ランキングを表示")
    @app_commands.guild_only()
    @app_commands.describe(
        category="ランキングの種類",
        period="集計期間",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="学習時間", value="study"),
            app_commands.Choice(name="XP", value="xp"),
            app_commands.Choice(name="タスク完了数", value="tasks"),
        ],
        period=[
            app_commands.Choice(name="今週", value="weekly"),
            app_commands.Choice(name="今月", value="monthly"),
            app_commands.Choice(name="全期間", value="all_time"),
        ],
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        category: str = "study",
        period: str = "weekly",
    ):
        await interaction.response.defer()

        days = PERIOD_DAYS.get(period, 7)
        period_label = PERIOD_LABELS.get(period, period)
        entries: list[dict] = []
        user_rank = 0

        if category == "study":
            ranking = await self.study_repo.get_guild_ranking(interaction.guild_id, days, limit=50)
            for i, row in enumerate(ranking):
                hours = row["total_minutes"] // 60
                mins = row["total_minutes"] % 60
                row["display_value"] = f"{hours}h {mins}m ({row['session_count']}回)"
                if row["user_id"] == interaction.user.id:
                    user_rank = i + 1
            entries = ranking
            title = f"📊 学習時間ランキング - {period_label}"

        elif category == "xp":
            ranking = await self.gamification_repo.get_xp_ranking(interaction.guild_id, limit=50)
            for i, row in enumerate(ranking):
                row["display_value"] = f"Lv.{row['level']} ({row['xp']:,} XP)"
                if row["user_id"] == interaction.user.id:
                    user_rank = i + 1
            entries = ranking
            title = f"⭐ XPランキング - {period_label}"

        elif category == "tasks":
            # タスク完了ランキングはstudy_logsと同様にJOINで集計
            ranking = await self._get_task_ranking(interaction.guild_id, days)
            for i, row in enumerate(ranking):
                row["display_value"] = f"{row['completed_count']}件完了"
                if row["user_id"] == interaction.user.id:
                    user_rank = i + 1
            entries = ranking
            title = f"✅ タスク完了ランキング - {period_label}"

        view = LeaderboardView(entries, title, interaction.user.id, user_rank)
        await interaction.followup.send(embed=view.build_embed(), view=view)

    async def _get_task_ranking(self, guild_id: int, days: int, limit: int = 50) -> list[dict]:
        """タスク完了ランキングを取得"""
        async with self.study_repo.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    t.user_id,
                    u.username,
                    COUNT(*) AS completed_count
                FROM todos t
                JOIN users u ON u.user_id = t.user_id
                WHERE t.guild_id = $1
                  AND t.status = 'completed'
                  AND t.completed_at >= CURRENT_TIMESTAMP - ($2 || ' days')::interval
                GROUP BY t.user_id, u.username
                ORDER BY completed_count DESC
                LIMIT $3
                """,
                guild_id,
                str(days),
                limit,
            )
        return [dict(row) for row in rows]

    def _find_leaderboard_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """リーダーボード投稿先チャンネルを検索"""
        for name in ("leaderboard", "study-log"):
            for channel in guild.text_channels:
                if channel.name == name:
                    return channel
        return None

    @tasks.loop(time=time(hour=22, minute=0, tzinfo=JST))
    async def daily_leaderboard_post(self):
        """毎日22:00 JSTにデイリーXPランキングを自動投稿"""
        top_earners = await self.gamification_repo.get_daily_top_earners(limit=5)

        if not top_earners:
            return

        lines = []
        for i, entry in enumerate(top_earners):
            medal = MEDAL_EMOJIS[i] if i < len(MEDAL_EMOJIS) else f"`{i + 1}.`"
            name = entry.get("username", "Unknown")
            xp = entry.get("daily_xp", 0)
            lines.append(f"{medal} **{name}** - {xp:,} XP")

        description = "\n".join(lines)

        embed = discord.Embed(
            title="📊 本日のXPランキング",
            description=description,
            color=COLORS["xp"],
        )
        embed.set_footer(text="明日もがんばろう！")

        for guild in self.bot.guilds:
            channel = self._find_leaderboard_channel(guild)
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    logger.debug("チャンネル送信不可: guild=%d", guild.id)
                except Exception:
                    logger.warning(
                        "デイリーリーダーボード投稿失敗: guild=%d",
                        guild.id,
                        exc_info=True,
                    )

    @daily_leaderboard_post.before_loop
    async def before_daily_leaderboard_post(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    await bot.add_cog(LeaderboardCog(bot, db_pool))
