"""AIドキュメント解析 Cog"""

import logging

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.ai_doc_manager import AIDocManager
from studybot.utils.embed_helper import error_embed

logger = logging.getLogger(__name__)


class AIDocCog(commands.Cog):
    """AIドキュメント解析機能"""

    def __init__(self, bot: commands.Bot, manager: AIDocManager) -> None:
        self.bot = bot
        self.manager = manager

    ai_group = app_commands.Group(name="ai", description="AIドキュメント解析")

    @ai_group.command(name="summarize", description="ファイルをAIで要約")
    @app_commands.describe(
        file="要約するファイル（PDF/テキスト）",
        detail_level="要約の詳細度",
    )
    @app_commands.choices(
        detail_level=[
            app_commands.Choice(name="簡潔", value="brief"),
            app_commands.Choice(name="標準", value="medium"),
            app_commands.Choice(name="詳細", value="detailed"),
        ]
    )
    async def ai_summarize(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        detail_level: str = "medium",
    ):
        # ファイルサイズチェック（10MB）
        if file.size > 10 * 1024 * 1024:
            await interaction.response.send_message(
                embed=error_embed("エラー", "ファイルサイズは10MB以下にしてください。"),
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # ファイルダウンロード
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file.url) as resp:
                    content = await resp.read()
        except Exception as e:
            logger.error(f"ファイルダウンロードエラー: {e}")
            await interaction.followup.send(
                embed=error_embed("エラー", "ファイルのダウンロードに失敗しました。")
            )
            return

        result = await self.manager.summarize(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            file_content=content,
            filename=file.filename,
            detail_level=detail_level,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("エラー", result["error"]))
            return

        detail_labels = {"brief": "簡潔", "medium": "標準", "detailed": "詳細"}
        cache_tag = " (キャッシュ)" if result.get("cached") else ""

        embed = discord.Embed(
            title=f"📄 AI要約 - {file.filename}{cache_tag}",
            description=result["summary"][:4000],
            color=COLORS["study"],
        )
        detail_label = detail_labels.get(detail_level, detail_level)
        footer = f"詳細度: {detail_label} | {interaction.user.display_name}"
        embed.set_footer(text=footer)
        await interaction.followup.send(embed=embed)

    @ai_group.command(name="keypoints", description="ファイルからキーポイントを抽出")
    @app_commands.describe(file="解析するファイル（PDF/テキスト）")
    async def ai_keypoints(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
    ):
        if file.size > 10 * 1024 * 1024:
            await interaction.response.send_message(
                embed=error_embed("エラー", "ファイルサイズは10MB以下にしてください。"),
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file.url) as resp:
                    content = await resp.read()
        except Exception as e:
            logger.error(f"ファイルダウンロードエラー: {e}")
            await interaction.followup.send(
                embed=error_embed("エラー", "ファイルのダウンロードに失敗しました。")
            )
            return

        result = await self.manager.extract_keypoints(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            file_content=content,
            filename=file.filename,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("エラー", result["error"]))
            return

        cache_tag = " (キャッシュ)" if result.get("cached") else ""

        embed = discord.Embed(
            title=f"🔑 キーポイント - {file.filename}{cache_tag}",
            description=result["keypoints"][:4000],
            color=COLORS["study"],
        )
        embed.set_footer(text=interaction.user.display_name)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = AIDocManager(db_pool)
    await bot.add_cog(AIDocCog(bot, manager))
