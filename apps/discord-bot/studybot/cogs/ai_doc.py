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


class QuizView(discord.ui.View):
    """クイズ表示ビュー"""

    def __init__(
        self,
        user_id: int,
        questions: list[dict],
        current_index: int = 0,
        score: int = 0,
    ) -> None:
        super().__init__(timeout=300)
        self.user_id = user_id
        self.questions = questions
        self.current_index = current_index
        self.score = score

        # 選択肢ボタンを追加
        q = self.questions[self.current_index]
        for choice in q.get("choices", []):
            label_letter = choice[0] if choice else "?"
            button = discord.ui.Button(
                label=choice,
                style=discord.ButtonStyle.secondary,
                custom_id=f"quiz_{label_letter}",
            )
            button.callback = self._make_callback(label_letter)
            self.add_item(button)

    def _make_callback(self, selected: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message(
                    embed=error_embed("エラー", "このクイズは他のユーザーのものです。"),
                    ephemeral=True,
                )
                return

            q = self.questions[self.current_index]
            correct = q.get("answer", "")
            is_correct = selected == correct

            if is_correct:
                self.score += 1

            result_icon = "⭕" if is_correct else "❌"
            explanation = q.get("explanation", "")

            embed = discord.Embed(
                title=f"{result_icon} 問題 {self.current_index + 1}/{len(self.questions)}",
                description=(
                    f"**{q['question']}**\n\n"
                    f"あなたの回答: {selected}\n"
                    f"正解: {correct}\n\n"
                    f"**解説:** {explanation}"
                ),
                color=COLORS["success"] if is_correct else COLORS["error"],
            )

            next_index = self.current_index + 1

            if next_index < len(self.questions):
                # 次の問題へ
                next_q = self.questions[next_index]
                next_view = QuizView(
                    user_id=self.user_id,
                    questions=self.questions,
                    current_index=next_index,
                    score=self.score,
                )
                embed.set_footer(text="次の問題が下に表示されます")

                next_embed = discord.Embed(
                    title=f"📝 問題 {next_index + 1}/{len(self.questions)}",
                    description=next_q["question"],
                    color=COLORS["study"],
                )
                await interaction.response.edit_message(embed=next_embed, view=next_view)
            else:
                # クイズ完了
                embed = discord.Embed(
                    title="🏆 クイズ完了！",
                    description=(
                        f"**スコア: {self.score}/{len(self.questions)} 正解！**\n\n"
                        f"正答率: {round(self.score / len(self.questions) * 100)}%"
                    ),
                    color=COLORS["success"]
                    if self.score >= len(self.questions) // 2
                    else COLORS["warning"],
                )
                await interaction.response.edit_message(embed=embed, view=None)

        return callback


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

    @ai_group.command(name="quiz", description="ファイルからクイズを生成")
    @app_commands.describe(
        file="クイズ元のファイル（PDF/テキスト）",
        count="問題数（1-10、デフォルト5）",
    )
    async def ai_quiz(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        count: int = 5,
    ):
        if file.size > 10 * 1024 * 1024:
            await interaction.response.send_message(
                embed=error_embed("エラー", "ファイルサイズは10MB以下にしてください。"),
                ephemeral=True,
            )
            return

        if not 1 <= count <= 10:
            await interaction.response.send_message(
                embed=error_embed("エラー", "問題数は1〜10の範囲で指定してください。"),
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

        result = await self.manager.generate_quiz(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            file_content=content,
            filename=file.filename,
            count=count,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("エラー", result["error"]))
            return

        questions = result["questions"]
        if not questions:
            await interaction.followup.send(
                embed=error_embed("エラー", "クイズの生成に失敗しました。")
            )
            return

        # 最初の問題を表示
        first_q = questions[0]
        embed = discord.Embed(
            title=f"📝 問題 1/{len(questions)}",
            description=first_q["question"],
            color=COLORS["study"],
        )
        embed.set_footer(text=f"{file.filename} から生成")

        view = QuizView(
            user_id=interaction.user.id,
            questions=questions,
        )
        await interaction.followup.send(embed=embed, view=view)

    @ai_group.command(name="ask", description="ファイルについて質問")
    @app_commands.describe(
        file="質問対象のファイル（PDF/テキスト）",
        question="質問内容",
    )
    async def ai_ask(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        question: str,
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

        result = await self.manager.ask_question(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            file_content=content,
            filename=file.filename,
            question=question,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("エラー", result["error"]))
            return

        embed = discord.Embed(
            title=f"💡 回答 - {file.filename}",
            color=COLORS["study"],
        )
        embed.add_field(name="質問", value=question, inline=False)
        embed.add_field(name="回答", value=result["answer"][:1024], inline=False)
        embed.set_footer(text=interaction.user.display_name)
        await interaction.followup.send(embed=embed)

    @ai_group.command(name="explain", description="概念をAIで解説")
    @app_commands.describe(concept="解説してほしい概念やキーワード")
    async def ai_explain(
        self,
        interaction: discord.Interaction,
        concept: str,
    ):
        await interaction.response.defer()

        result = await self.manager.explain_concept(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            concept=concept,
        )

        if "error" in result:
            await interaction.followup.send(embed=error_embed("エラー", result["error"]))
            return

        embed = discord.Embed(
            title=f"📖 解説: {concept}",
            description=result["explanation"][:4000],
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
