"""フォージ Cog - 熟練の鍛冶場"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import COLORS
from studybot.managers.forge_manager import (
    MASTERY_LEVELS,
    SKILL_CATEGORIES,
    ForgeManager,
)
from studybot.utils.embed_helper import error_embed, success_embed

logger = logging.getLogger(__name__)


class PracticeModal(discord.ui.Modal, title="意図的練習ログ"):
    """意図的練習の自己評価入力"""

    focus = discord.ui.TextInput(
        label="集中度 (1-5)",
        placeholder="1=散漫, 3=普通, 5=完全に集中",
        max_length=1,
        required=True,
    )
    difficulty = discord.ui.TextInput(
        label="難易度 (1-5)",
        placeholder="1=簡単すぎ, 3=ちょうど良い, 5=難しすぎ",
        max_length=1,
        required=True,
    )
    progress = discord.ui.TextInput(
        label="進歩度 (1-5)",
        placeholder="1=停滞, 3=少し進歩, 5=大きな進歩",
        max_length=1,
        required=True,
    )
    duration = discord.ui.TextInput(
        label="学習時間（分）",
        placeholder="例: 30",
        max_length=3,
        required=True,
    )

    def __init__(self, cog: "ForgeCog", category: str) -> None:
        super().__init__()
        self.cog = cog
        self.category = category

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            focus = int(self.focus.value)
            difficulty = int(self.difficulty.value)
            progress = int(self.progress.value)
            duration = int(self.duration.value)

            if not all(1 <= v <= 5 for v in [focus, difficulty, progress]):
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

        result = await self.cog.manager.log_practice(
            interaction.user.id,
            self.category,
            focus,
            difficulty,
            progress,
            duration,
        )

        cat_info = SKILL_CATEGORIES.get(self.category, {})
        level = result["mastery_level"]

        embed = discord.Embed(
            title="🔨 練習ログ記録完了",
            description=(
                f"スキル: {cat_info.get('emoji', '📚')} {cat_info.get('name', self.category)}\n"
                f"品質スコア: **{result['quality_score']:.0f}**点\n"
                f"マスタリーXP: +{result['mastery_xp_gained']}"
            ),
            color=COLORS["forge"],
        )
        embed.add_field(
            name="マスタリー",
            value=f"{level['emoji']} {level['name']} ({result['total_mastery_xp']} XP)",
            inline=True,
        )
        embed.add_field(
            name="品質平均",
            value=f"{result['quality_avg']:.0f}点",
            inline=True,
        )

        if result["leveled_up"]:
            embed.add_field(
                name="🎉 レベルアップ！",
                value=f"**{level['name']}** に到達しました！",
                inline=False,
            )

        # ウェルネス推奨表示
        wellness_cog = self.cog.bot.get_cog("WellnessCog")
        if wellness_cog:
            try:
                rec = await wellness_cog.manager.get_recommendation(interaction.user.id)
                if rec and rec.get("session_type") in ("light", "moderate"):
                    embed.add_field(
                        name="💡 ウェルネス推奨",
                        value="疲労が見られます。易しめの練習がおすすめです",
                        inline=False,
                    )
            except Exception:
                pass

        await interaction.response.send_message(embed=embed)


class ReviewModal(discord.ui.Modal, title="ピアレビュー"):
    """ピアレビューの評価入力"""

    quality_rating = discord.ui.TextInput(
        label="品質評価 (1-5)",
        placeholder="1=要改善, 3=良い, 5=素晴らしい",
        max_length=1,
        required=True,
    )
    feedback = discord.ui.TextInput(
        label="フィードバック",
        style=discord.TextStyle.paragraph,
        placeholder="具体的なフィードバックを書きましょう",
        max_length=1000,
        required=True,
    )

    def __init__(self, cog: "ForgeCog", submission_id: int) -> None:
        super().__init__()
        self.cog = cog
        self.submission_id = submission_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            rating = int(self.quality_rating.value)
            if not 1 <= rating <= 5:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed("入力エラー", "品質評価は1-5の数値を入力してください"),
                ephemeral=True,
            )
            return

        result = await self.cog.manager.complete_review(
            interaction.user.id,
            self.submission_id,
            rating,
            self.feedback.value,
        )

        if not result:
            await interaction.response.send_message(
                embed=error_embed("エラー", "レビューの完了に失敗しました"),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔥 レビュー完了！",
            description=(
                f"提出者に **+{result['submitter_xp']}** マスタリーXP\n"
                f"あなたに **+{result['reviewer_xp']}** マスタリーXP"
            ),
            color=COLORS["forge"],
        )
        await interaction.response.send_message(embed=embed)


class ForgeCog(commands.Cog):
    """フォージ - 熟練の鍛冶場"""

    def __init__(self, bot: commands.Bot, manager: ForgeManager) -> None:
        self.bot = bot
        self.manager = manager

    # --- 外部連携メソッド ---

    async def record_quality(self, user_id: int, category: str, minutes: int) -> None:
        """gamificationフック: 学習品質記録"""
        try:
            await self.manager.record_study_quality(user_id, category, minutes)
        except Exception:
            logger.debug("品質記録失敗 (user=%d)", user_id, exc_info=True)

    # --- コマンド ---

    forge_group = app_commands.Group(name="forge", description="フォージ - 熟練の鍛冶場")

    @forge_group.command(name="skills", description="マスタリーツリー表示")
    @app_commands.describe(category="スキルカテゴリ")
    @app_commands.choices(
        category=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in SKILL_CATEGORIES.items()
        ]
    )
    async def skills(self, interaction: discord.Interaction, category: str = "") -> None:
        await interaction.response.defer()

        skills = await self.manager.get_skills(interaction.user.id, category)

        embed = discord.Embed(
            title="🔨 マスタリーツリー",
            description=f"{interaction.user.display_name}のスキル",
            color=COLORS["forge"],
        )

        if not skills:
            embed.description += (
                "\n\nまだスキルがありません。`/forge practice` で練習を始めましょう！"
            )
        else:
            for s in skills:
                cat_info = s.get("category_info", {})
                level = s.get("level_info", MASTERY_LEVELS[0])
                ptn = s.get("progress_to_next", 0)
                bar_filled = ptn // 20
                bar = "🟧" * bar_filled + "⬜" * (5 - bar_filled)

                next_info = ""
                if s.get("next_level"):
                    next_info = f"\n次: {s['next_level']['name']} {bar} {ptn}%"

                embed.add_field(
                    name=f"{cat_info.get('emoji', '📚')} {cat_info.get('name', s['category'])}",
                    value=(
                        f"{level['emoji']} **{level['name']}** "
                        f"({s.get('mastery_xp', 0)} XP)\n"
                        f"品質平均: {s.get('quality_avg', 0):.0f}点"
                        f"{next_info}"
                    ),
                    inline=True,
                )

        await interaction.followup.send(embed=embed)

    @forge_group.command(name="practice", description="意図的練習ログ")
    @app_commands.describe(skill="練習するスキル")
    @app_commands.choices(
        skill=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in SKILL_CATEGORIES.items()
        ]
    )
    async def practice(self, interaction: discord.Interaction, skill: str) -> None:
        if skill not in SKILL_CATEGORIES:
            await interaction.response.send_message(
                embed=error_embed("エラー", "不明なスキルカテゴリです"),
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(PracticeModal(self, skill))

    @forge_group.command(name="quality", description="品質スコアトレンド")
    async def quality(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        trend = await self.manager.get_quality_trend(interaction.user.id)
        if not trend:
            await interaction.followup.send(
                embed=error_embed(
                    "データなし",
                    "まだ品質ログがありません。`/forge practice` で練習を始めましょう！",
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔨 品質スコアトレンド（7日間）",
            color=COLORS["forge"],
        )

        trend_text = ""
        for day in trend:
            avg = float(day["avg_quality"])
            sessions = day["sessions"]
            bar_filled = int(avg / 20)
            bar = "🟧" * bar_filled + "⬜" * (5 - bar_filled)
            trend_text += f"`{day['day']}` {bar} {avg:.0f}pt ({sessions}回)\n"

        embed.description = trend_text
        await interaction.followup.send(embed=embed)

    @forge_group.command(name="ladder", description="チャレンジラダー順位表")
    @app_commands.describe(category="スキルカテゴリ")
    @app_commands.choices(
        category=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in SKILL_CATEGORIES.items()
        ]
    )
    async def ladder(self, interaction: discord.Interaction, category: str = "general") -> None:
        await interaction.response.defer()

        leaderboard = await self.manager.get_leaderboard(category)
        user_rating = await self.manager.get_rating(interaction.user.id, category)

        cat_info = SKILL_CATEGORIES.get(category, {})
        embed = discord.Embed(
            title=f"🏆 {cat_info.get('name', category)} ラダー",
            color=COLORS["forge"],
        )

        if not leaderboard:
            embed.description = "まだランキングデータがありません"
        else:
            medals = ["🥇", "🥈", "🥉"]
            text = ""
            for i, entry in enumerate(leaderboard):
                medal = medals[i] if i < 3 else f"`{i + 1}.`"
                text += (
                    f"{medal} **{entry.get('username', 'Unknown')}** "
                    f"- {entry['rating']} "
                    f"({entry['wins']}W {entry['losses']}L)\n"
                )
            embed.description = text

        embed.add_field(
            name="あなたのレーティング",
            value=f"**{user_rating['rating']}** ({user_rating['wins']}W {user_rating['losses']}L)",
            inline=False,
        )
        await interaction.followup.send(embed=embed)

    @forge_group.command(name="profile", description="鍛冶プロフィール")
    async def profile(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        data = await self.manager.get_profile(interaction.user.id)

        embed = discord.Embed(
            title=f"🔨 {interaction.user.display_name}の鍛冶場",
            description=f"総合品質平均: **{data['overall_quality_avg']:.0f}**点",
            color=COLORS["forge"],
        )

        if data["skills"]:
            skill_text = ""
            for s in data["skills"][:6]:
                cat = s.get("category_info", {})
                level = s.get("level_info", MASTERY_LEVELS[0])
                skill_text += (
                    f"{cat.get('emoji', '📚')} {cat.get('name', '?')}: "
                    f"{level['emoji']} {level['name']} "
                    f"({s.get('mastery_xp', 0)} XP)\n"
                )
            embed.add_field(name="スキル", value=skill_text, inline=False)

        if data["recent_logs"]:
            log_text = ""
            for log in data["recent_logs"][:3]:
                cat_info = SKILL_CATEGORIES.get(log["category"], {})
                log_text += (
                    f"{cat_info.get('emoji', '📚')} "
                    f"品質{log['quality_score']:.0f} | "
                    f"集中{log['focus']} 難易度{log['difficulty']} "
                    f"進歩{log['progress']}\n"
                )
            embed.add_field(name="最近の練習", value=log_text, inline=False)

        embed.set_footer(text="品質を重視した意図的練習で成長しよう")
        await interaction.followup.send(embed=embed)

    # --- チャレンジサブグループ ---

    challenge_group = app_commands.Group(
        name="challenge",
        description="フォージチャレンジ",
        parent=forge_group,
    )

    @challenge_group.command(name="list", description="チャレンジ一覧")
    @app_commands.describe(category="カテゴリフィルター")
    @app_commands.choices(
        category=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in SKILL_CATEGORIES.items()
        ]
    )
    async def challenge_list(self, interaction: discord.Interaction, category: str = "") -> None:
        await interaction.response.defer()

        challenges = await self.manager.list_challenges(category)
        if not challenges:
            await interaction.followup.send(
                embed=error_embed(
                    "チャレンジなし",
                    "まだチャレンジがありません。",
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔨 チャレンジ一覧",
            color=COLORS["forge"],
        )

        for c in challenges[:10]:
            cat_info = c.get("category_info", {})
            embed.add_field(
                name=(f"{cat_info.get('emoji', '📚')} [{c['id']}] {c['title']}"),
                value=(
                    f"{c['description']}\n"
                    f"難易度: **{c['difficulty_rating']}** | "
                    f"成功率: {c['success_rate']}% "
                    f"({c['attempt_count']}回挑戦)"
                ),
                inline=False,
            )

        embed.set_footer(text="/forge challenge attempt <id> <pass/fail> で挑戦")
        await interaction.followup.send(embed=embed)

    @challenge_group.command(name="attempt", description="チャレンジに挑戦")
    @app_commands.describe(
        challenge_id="チャレンジID",
        result="結果（pass=合格, fail=不合格）",
    )
    @app_commands.choices(
        result=[
            app_commands.Choice(name="合格 (pass)", value="pass"),
            app_commands.Choice(name="不合格 (fail)", value="fail"),
        ]
    )
    async def challenge_attempt(
        self,
        interaction: discord.Interaction,
        challenge_id: int,
        result: str,
    ) -> None:
        await interaction.response.defer()

        passed = result == "pass"
        attempt = await self.manager.attempt_challenge(interaction.user.id, challenge_id, passed)

        if not attempt:
            await interaction.followup.send(
                embed=error_embed(
                    "エラー",
                    "チャレンジが見つからないか、無効です。",
                ),
                ephemeral=True,
            )
            return

        challenge = attempt["challenge"]
        emoji = "✅" if passed else "❌"
        rating_change = attempt["user_rating_change"]
        change_str = f"+{rating_change}" if rating_change >= 0 else str(rating_change)

        embed = discord.Embed(
            title=f"{emoji} {challenge['title']}",
            description=(
                f"結果: **{'合格' if passed else '不合格'}**\n"
                f"レーティング: {attempt['user_rating']} ({change_str})\n"
                f"マスタリーXP: +{attempt['mastery_xp_gained']}"
            ),
            color=COLORS["forge"],
        )
        await interaction.followup.send(embed=embed)

    @challenge_group.command(name="create", description="チャレンジ作成")
    @app_commands.describe(
        title="チャレンジ名",
        description="説明",
        category="カテゴリ",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in SKILL_CATEGORIES.items()
        ]
    )
    async def challenge_create(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        category: str,
    ) -> None:
        challenge = await self.manager.create_challenge(
            interaction.user.id, title, description, category
        )

        if not challenge:
            await interaction.response.send_message(
                embed=error_embed(
                    "作成失敗",
                    "タイトルが空か、カテゴリが不正です。",
                ),
                ephemeral=True,
            )
            return

        embed = success_embed(
            "チャレンジ作成完了！",
            f"**{challenge['title']}** (ID: {challenge['id']})\n"
            f"カテゴリ: {SKILL_CATEGORIES.get(category, {}).get('name', category)}",
        )
        await interaction.response.send_message(embed=embed)

    # --- ピアレビューサブグループ ---

    review_group = app_commands.Group(
        name="review",
        description="ピアレビュー (The Crucible)",
        parent=forge_group,
    )

    @review_group.command(name="submit", description="作品をレビューに提出")
    @app_commands.describe(
        category="カテゴリ",
        title="作品タイトル",
        description="作品の説明",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in SKILL_CATEGORIES.items()
        ]
    )
    async def review_submit(
        self,
        interaction: discord.Interaction,
        category: str,
        title: str,
        description: str,
    ) -> None:
        submission = await self.manager.submit_for_review(
            interaction.user.id, category, title, description
        )

        if not submission:
            await interaction.response.send_message(
                embed=error_embed(
                    "提出失敗",
                    "カテゴリが不正か、タイトル/説明が空です。",
                ),
                ephemeral=True,
            )
            return

        embed = success_embed(
            "レビュー提出完了！",
            f"**{submission['title']}** (ID: {submission['id']})\n"
            "他のユーザーがレビューしてくれるのを待ちましょう！",
        )
        await interaction.response.send_message(embed=embed)

    @review_group.command(name="list", description="レビュー待ち作品一覧")
    @app_commands.describe(category="カテゴリフィルター")
    @app_commands.choices(
        category=[
            app_commands.Choice(name=f"{v['emoji']} {v['name']}", value=k)
            for k, v in SKILL_CATEGORIES.items()
        ]
    )
    async def review_list(self, interaction: discord.Interaction, category: str = "") -> None:
        await interaction.response.defer()

        submissions = await self.manager.repository.get_open_submissions(
            category, interaction.user.id
        )

        if not submissions:
            await interaction.followup.send(
                embed=error_embed(
                    "作品なし",
                    "レビュー待ちの作品はありません。",
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔥 レビュー待ち作品",
            color=COLORS["forge"],
        )

        for s in submissions[:10]:
            cat_info = SKILL_CATEGORIES.get(s["category"], {})
            embed.add_field(
                name=f"{cat_info.get('emoji', '📚')} [{s['id']}] {s['title']}",
                value=s["description"][:100],
                inline=False,
            )

        embed.set_footer(text="/forge review claim <id> でレビューを引き受け")
        await interaction.followup.send(embed=embed)

    @review_group.command(name="claim", description="レビューを引き受け")
    @app_commands.describe(submission_id="作品ID")
    async def review_claim(self, interaction: discord.Interaction, submission_id: int) -> None:
        submission = await self.manager.claim_review(interaction.user.id, submission_id)

        if not submission:
            await interaction.response.send_message(
                embed=error_embed(
                    "引き受け失敗",
                    "作品が見つからない、自分の作品、または既に引き受け済みです。",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(ReviewModal(self, submission_id))


async def setup(bot: commands.Bot) -> None:
    manager = ForgeManager(bot.db_pool)
    # テンプレートチャレンジを投入
    try:
        await manager.seed_challenges()
    except Exception:
        logger.warning("チャレンジシード失敗（既存データがある場合は正常）", exc_info=True)
    await bot.add_cog(ForgeCog(bot, manager))
