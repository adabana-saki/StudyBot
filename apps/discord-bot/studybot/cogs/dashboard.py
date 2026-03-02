"""ダッシュボード Cog

Web UIへのリンクをボタン付きEmbedで表示する。
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.config.settings import settings

logger = logging.getLogger(__name__)

WEB_PAGES = [
    ("📊", "ダッシュボード", "/dashboard", "学習時間・ストリーク・レベルを一覧表示"),
    ("🏆", "リーダーボード", "/leaderboard", "サーバー内ランキング"),
    ("🃏", "フラッシュカード", "/flashcards", "間隔反復学習で記憶定着"),
    ("✅", "To-Do", "/todos", "タスク管理"),
    ("🧘", "ウェルネス", "/wellness", "気分・エネルギー・ストレスの記録"),
    ("🎯", "フォーカス", "/focus", "フォーカスロック"),
    ("📈", "インサイト", "/insights", "AI学習分析・週次レポート"),
    ("🏪", "ショップ", "/shop", "アイテム購入"),
    ("📉", "投資市場", "/market", "学習株式・貯金・フリマ"),
]


class DashboardLinkView(discord.ui.View):
    """Web UIへのリンクボタンを並べるView"""

    def __init__(self, base_url: str) -> None:
        super().__init__(timeout=None)

        # 1行目: メイン
        self.add_item(
            discord.ui.Button(
                label="ダッシュボードを開く",
                emoji="🌐",
                url=f"{base_url}/dashboard",
                style=discord.ButtonStyle.link,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="リーダーボード",
                emoji="🏆",
                url=f"{base_url}/leaderboard",
                style=discord.ButtonStyle.link,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="フラッシュカード",
                emoji="🃏",
                url=f"{base_url}/flashcards",
                style=discord.ButtonStyle.link,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="To-Do",
                emoji="✅",
                url=f"{base_url}/todos",
                style=discord.ButtonStyle.link,
            )
        )

        # 2行目: サブ
        self.add_item(
            discord.ui.Button(
                label="ウェルネス",
                emoji="🧘",
                url=f"{base_url}/wellness",
                style=discord.ButtonStyle.link,
                row=1,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="フォーカス",
                emoji="🎯",
                url=f"{base_url}/focus",
                style=discord.ButtonStyle.link,
                row=1,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="ショップ",
                emoji="🏪",
                url=f"{base_url}/shop",
                style=discord.ButtonStyle.link,
                row=1,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="投資市場",
                emoji="📉",
                url=f"{base_url}/market",
                style=discord.ButtonStyle.link,
                row=1,
            )
        )


class DashboardCog(commands.Cog):
    """Web UIダッシュボードへの導線"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.web_url = settings.WEB_BASE_URL.rstrip("/")

    @app_commands.command(name="dashboard", description="Web UIのダッシュボードを開く")
    async def dashboard_command(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="🌐 StudyBot Web Dashboard",
            description=(
                "ブラウザでStudyBotの全機能にアクセスできます。\n"
                "下のボタンから各ページに直接ジャンプ！\n\n"
                + "\n".join(f"{emoji} **{name}** — {desc}" for emoji, name, _, desc in WEB_PAGES)
            ),
            color=COLORS["primary"],
            url=f"{self.web_url}/dashboard",
        )
        embed.set_footer(text=f"URL: {self.web_url}")

        view = DashboardLinkView(self.web_url)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    """DashboardCogをBotに登録する。"""
    await bot.add_cog(DashboardCog(bot))
