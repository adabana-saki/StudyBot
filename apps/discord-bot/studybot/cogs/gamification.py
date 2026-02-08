"""ゲーミフィケーション（XP/レベル）Cog"""

import logging
from datetime import date, time, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COIN_REWARDS, COLORS, RAID_DEFAULTS, XP_REWARDS
from studybot.managers.gamification_manager import GamificationManager
from studybot.repositories.nudge_repository import NudgeRepository
from studybot.utils.embed_helper import error_embed, help_embed, info_embed, xp_embed

JST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)


def _progress_bar(current: int, target: int, width: int = 15) -> str:
    """レベル進捗バー"""
    ratio = min(1.0, current / target) if target > 0 else 0
    filled = int(width * ratio)
    bar = "▓" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{target} XP"


class ProfileEditModal(discord.ui.Modal, title="プロフィール編集"):
    """プロフィール編集モーダル"""

    bio_input = discord.ui.TextInput(
        label="自己紹介",
        placeholder="例: 毎日プログラミングを勉強しています！",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=200,
    )
    title_input = discord.ui.TextInput(
        label="カスタム称号",
        placeholder="例: Python マスター",
        required=False,
        max_length=100,
    )
    timezone_input = discord.ui.TextInput(
        label="タイムゾーン",
        placeholder="Asia/Tokyo",
        default="Asia/Tokyo",
        required=False,
        max_length=50,
    )
    goal_input = discord.ui.TextInput(
        label="日目標（分）",
        placeholder="60",
        default="60",
        required=False,
        max_length=5,
    )

    def __init__(self, cog: "GamificationCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        shop_cog = self.cog.bot.get_cog("ShopCog")
        if not shop_cog:
            await interaction.response.send_message(
                embed=error_embed("エラー", "プロフィール編集機能は現在利用できません。"),
                ephemeral=True,
            )
            return

        daily_goal = 60
        if self.goal_input.value.strip():
            try:
                daily_goal = int(self.goal_input.value.strip())
                daily_goal = max(10, min(daily_goal, 720))
            except ValueError:
                daily_goal = 60

        await shop_cog.manager.update_user_preferences(
            interaction.user.id,
            bio=self.bio_input.value or "",
            custom_title=self.title_input.value or None,
            timezone=self.timezone_input.value or "Asia/Tokyo",
            daily_goal_minutes=daily_goal,
        )

        from studybot.utils.embed_helper import success_embed

        embed = success_embed(
            "プロフィール更新完了",
            "プロフィールを更新しました！\n`/profile` で確認できます。",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GamificationCog(commands.Cog):
    """XP & レベルシステム"""

    def __init__(self, bot: commands.Bot, manager: GamificationManager) -> None:
        self.bot = bot
        self.manager = manager
        self.nudge_repo = NudgeRepository(manager.repository.db_pool)

    async def cog_load(self) -> None:
        self.streak_protection_dm.start()
        self.churn_detection_dm.start()

    async def cog_unload(self) -> None:
        self.streak_protection_dm.cancel()
        self.churn_detection_dm.cancel()

    # --- ウェルカムガイド ---

    async def _ensure_user_and_welcome(
        self, interaction: discord.Interaction, user_id: int, username: str
    ) -> None:
        """ensure_user を呼び出し、新規ユーザーならウェルカムDMを送信"""
        _, is_new = await self.manager.ensure_user(user_id, username)
        if is_new:
            try:
                await self.send_welcome_guide(interaction.user)
            except Exception:
                logger.debug("ウェルカムガイド送信失敗 (user=%d)", user_id, exc_info=True)

    async def send_welcome_guide(self, user: discord.User) -> None:
        """初回ウェルカムガイドをDMで送信"""
        embed = help_embed(
            "StudyBot へようこそ！",
            (
                "学習をゲーム感覚で楽しく続けられるBotです。\n"
                "まずは以下を試してみましょう：\n\n"
                "1️⃣ `/pomodoro start` - ポモドーロタイマーを開始\n"
                "2️⃣ `/study log 30 数学` - 学習を記録\n"
                "3️⃣ `/todo quick 宿題を終わらせる` - タスクを追加\n"
                "4️⃣ `/profile` - プロフィールを確認\n"
                "5️⃣ `/quest daily` - デイリークエストを確認\n\n"
                "💡 `/help` でいつでもコマンド一覧を表示できます。\n"
                "頑張りましょう！"
            ),
        )
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            logger.debug("ウェルカムDM送信不可: user=%d", user.id)

    # --- コマンド ---

    @app_commands.command(name="streak", description="連続学習の詳細を表示")
    async def streak(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        await self._ensure_user_and_welcome(
            interaction, interaction.user.id, interaction.user.display_name
        )
        details = await self.manager.get_streak_details(interaction.user.id)

        if not details:
            await interaction.followup.send(
                embed=info_embed("🔥 ストリーク", "ストリーク情報が見つかりません。学習を始めましょう！"),
                ephemeral=True,
            )
            return

        streak = details["streak_days"]
        best = details["best_streak"]
        next_ms = details["next_milestone"]
        days_until = details["days_until_milestone"]

        # 火の絵文字スケーリング
        fire_count = max(1, streak // 7) if streak > 0 else 0
        fire_display = "🔥" * min(fire_count, 10) if fire_count > 0 else "—"

        embed = discord.Embed(
            title="🔥 連続学習ストリーク",
            color=COLORS["xp"],
        )

        embed.add_field(
            name="現在のストリーク",
            value=f"{fire_display}\n**{streak}日連続**",
            inline=True,
        )
        embed.add_field(
            name="最高記録",
            value=f"🏆 **{best}日**",
            inline=True,
        )

        if next_ms:
            # プログレスバー
            prev_milestones = [0, 7, 14, 30, 60, 100]
            prev_ms = 0
            for pm in prev_milestones:
                if pm < next_ms and streak >= pm:
                    prev_ms = pm
            progress_in_segment = streak - prev_ms
            segment_size = next_ms - prev_ms
            ratio = min(1.0, progress_in_segment / segment_size) if segment_size > 0 else 0
            filled = int(15 * ratio)
            bar = "▓" * filled + "░" * (15 - filled)
            embed.add_field(
                name=f"次のマイルストーン: {next_ms}日",
                value=f"[{bar}] あと**{days_until}日**",
                inline=False,
            )
        else:
            embed.add_field(
                name="マイルストーン",
                value="🎉 全マイルストーン達成！",
                inline=False,
            )

        embed.set_footer(text="毎日学習してストリークを伸ばそう！")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="プロフィールを表示")
    @app_commands.describe(user="表示するユーザー（省略で自分）")
    async def profile(self, interaction: discord.Interaction, user: discord.Member | None = None):
        await interaction.response.defer()

        target = user or interaction.user
        await self._ensure_user_and_welcome(interaction, target.id, target.display_name)
        profile = await self.manager.get_profile(target.id)

        if not profile:
            await interaction.followup.send(
                embed=info_embed("プロフィール", "プロフィールが見つかりません。学習を始めましょう！"),
                ephemeral=True,
            )
            return

        # ユーザー設定を取得
        prefs = None
        shop_cog = self.bot.get_cog("ShopCog")
        if shop_cog:
            try:
                prefs = await shop_cog.manager.get_user_preferences(target.id)
            except Exception:
                logger.debug("ユーザー設定取得失敗 (user=%d)", target.id, exc_info=True)

        title_text = f"{profile['badge']} {target.display_name}"
        if prefs and prefs.get("custom_title"):
            title_text = f"{profile['badge']} {target.display_name} | {prefs['custom_title']}"

        embed = discord.Embed(
            title=title_text,
            color=COLORS["xp"],
        )

        if prefs and prefs.get("bio"):
            embed.description = prefs["bio"]

        embed.add_field(name="レベル", value=f"Lv.{profile['level']}", inline=True)
        embed.add_field(name="総XP", value=f"{profile['xp']:,} XP", inline=True)
        embed.add_field(name="ランク", value=f"#{profile['rank']}", inline=True)
        embed.add_field(
            name="次のレベルまで",
            value=_progress_bar(profile["current_progress"], profile["next_level_xp"]),
            inline=False,
        )
        embed.add_field(
            name="連続学習",
            value=f"🔥 {profile['streak_days']}日",
            inline=True,
        )

        # フォーカススコア表示
        try:
            fs = await self.manager.calculate_focus_score(target.id)
            embed.add_field(
                name="フォーカススコア",
                value=f"🎯 **{fs['score']}** ({fs['grade']})",
                inline=True,
            )
        except Exception:
            logger.debug("フォーカススコア取得失敗 (user=%d)", target.id, exc_info=True)

        # 自己ベスト表示
        try:
            bests = await self.manager.get_personal_bests(target.id)
            best_parts = []
            if bests["best_streak"] > 0:
                best_parts.append(f"🔥 連続: {bests['best_streak']}日")
            if bests["best_daily_minutes"] > 0:
                best_parts.append(f"📚 日次: {bests['best_daily_minutes']}分")
            if bests["best_weekly_minutes"] > 0:
                best_parts.append(f"📅 週次: {bests['best_weekly_minutes']}分")
            if best_parts:
                embed.add_field(
                    name="自己ベスト",
                    value="\n".join(best_parts),
                    inline=False,
                )
        except Exception:
            logger.debug("自己ベスト取得失敗 (user=%d)", target.id, exc_info=True)

        # 装備アイテム表示
        if shop_cog:
            try:
                inventory = await shop_cog.manager.get_inventory(target.id)
                equipped = [i for i in inventory if i.get("equipped")]
                if equipped:
                    equip_text = ", ".join(f"{i['emoji']} {i['name']}" for i in equipped)
                    embed.add_field(name="装備", value=equip_text, inline=False)
            except Exception:
                logger.debug("装備アイテム取得失敗 (user=%d)", target.id, exc_info=True)

        embed.set_thumbnail(url=target.display_avatar.url)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="profile_edit", description="プロフィールを編集")
    async def profile_edit(self, interaction: discord.Interaction):
        """モーダルでプロフィールを編集"""
        await interaction.response.send_modal(ProfileEditModal(self))

    @app_commands.command(name="xp", description="現在のXPとレベルを表示")
    async def xp_command(self, interaction: discord.Interaction):
        await self._ensure_user_and_welcome(
            interaction, interaction.user.id, interaction.user.display_name
        )
        profile = await self.manager.get_profile(interaction.user.id)

        if not profile:
            await interaction.response.send_message(
                embed=info_embed("⭐ XP", "データが見つかりません。学習を始めましょう！"),
                ephemeral=True,
            )
            return

        embed = xp_embed(
            f"⭐ Lv.{profile['level']} - {profile['xp']:,} XP",
            _progress_bar(profile["current_progress"], profile["next_level_xp"]),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="focus_score", description="フォーカススコアの詳細を表示")
    async def focus_score_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        await self._ensure_user_and_welcome(
            interaction, interaction.user.id, interaction.user.display_name
        )

        fs = await self.manager.calculate_focus_score(interaction.user.id)
        c = fs["components"]

        embed = discord.Embed(
            title=f"🎯 フォーカススコア: {fs['score']} ({fs['grade']})",
            color=COLORS["xp"],
        )
        embed.add_field(
            name="内訳",
            value=(
                f"セッション完了率: **{c['completion_rate']}%**\n"
                f"ロック成功率: **{c['lock_success']}%**\n"
                f"学習一貫性: **{c['consistency']}%**\n"
                f"セッション質: **{c['session_quality']}%**"
            ),
            inline=False,
        )
        embed.set_footer(text="過去14日間のデータに基づいて算出")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="season", description="シーズンパスの進捗を表示")
    async def season_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        await self._ensure_user_and_welcome(
            interaction, interaction.user.id, interaction.user.display_name
        )

        progress = await self.manager.get_season_progress(interaction.user.id)
        if not progress:
            await interaction.followup.send(
                embed=info_embed(
                    "🏅 シーズンパス",
                    "現在アクティブなシーズンはありません。",
                ),
                ephemeral=True,
            )
            return

        season = progress["season"]
        total_xp = progress["total_xp"]
        current_tier = progress["tier"]
        next_tier = progress["next_tier"]

        # ティアラベルを取得
        from studybot.managers.gamification_manager import SEASON_TIERS
        tier_label = "未開始"
        for t in SEASON_TIERS:
            if t["tier"] == current_tier:
                tier_label = t["label"]
                break

        embed = discord.Embed(
            title=f"🏅 シーズンパス: {season['name']}",
            description=f"期間: {season['start_date']} 〜 {season['end_date']}",
            color=COLORS["xp"],
        )

        embed.add_field(
            name="現在のティア",
            value=f"**{tier_label}** (Tier {current_tier})",
            inline=True,
        )
        embed.add_field(
            name="シーズンXP",
            value=f"**{total_xp:,}** XP",
            inline=True,
        )

        if next_tier:
            xp_needed = next_tier["xp_required"] - total_xp
            ratio = min(1.0, total_xp / next_tier["xp_required"]) if next_tier["xp_required"] > 0 else 0
            filled = int(15 * ratio)
            bar = "▓" * filled + "░" * (15 - filled)
            embed.add_field(
                name=f"次のティア: {next_tier['label']}",
                value=f"[{bar}] あと **{max(0, xp_needed):,}** XP\n報酬: {next_tier['reward_coins']} 🪙",
                inline=False,
            )
        else:
            embed.add_field(
                name="🎉 最高ティア達成！",
                value="全てのシーズン報酬を獲得しました！",
                inline=False,
            )

        embed.set_footer(text="学習するたびにシーズンXPが貯まります")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="season_ranking", description="シーズンランキングを表示")
    async def season_ranking_command(self, interaction: discord.Interaction):
        await interaction.response.defer()

        leaderboard = await self.manager.get_season_leaderboard(10)
        if not leaderboard:
            await interaction.followup.send(
                embed=info_embed("🏅 シーズンランキング", "まだデータがありません。")
            )
            return

        embed = discord.Embed(
            title="🏅 シーズンランキング",
            color=COLORS["xp"],
        )
        medals = ["🥇", "🥈", "🥉"]
        for i, entry in enumerate(leaderboard[:10]):
            medal = medals[i] if i < 3 else f"#{i + 1}"
            embed.add_field(
                name=f"{medal} {entry['username']}",
                value=f"XP: {entry['total_xp']:,} | Tier {entry['tier']}",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="study_timing", description="最適な学習タイミングを分析")
    async def study_timing_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        await self._ensure_user_and_welcome(
            interaction, interaction.user.id, interaction.user.display_name
        )

        timing = await self.manager.get_optimal_timing(interaction.user.id)

        if not timing["has_data"]:
            await interaction.followup.send(
                embed=info_embed(
                    "⏰ 学習タイミング",
                    "まだ十分な学習データがありません。\n学習を記録してからお試しください！",
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="⏰ あなたの最適な学習タイミング",
            description="過去30日間の学習パターンを分析しました",
            color=COLORS["xp"],
        )

        # 時間帯
        if timing["best_hours"]:
            hour_text = "\n".join(
                f"**{h['label']}** - {h['total_minutes']}分 ({h['sessions']}回)"
                for h in timing["best_hours"]
            )
            embed.add_field(
                name="🕐 よく学習する時間帯",
                value=hour_text,
                inline=False,
            )

        # 曜日
        if timing["best_days"]:
            day_text = "\n".join(
                f"**{d['label']}** - {d['total_minutes']}分 ({d['sessions']}回)"
                for d in timing["best_days"]
            )
            embed.add_field(
                name="📅 よく学習する曜日",
                value=day_text,
                inline=False,
            )

        # ポモドーロ推奨
        embed.add_field(
            name="🍅 推奨ポモドーロ時間",
            value=(
                f"**{timing['recommended_pomo_minutes']}分**\n"
                f"(平均完了時間: {timing['avg_pomo_minutes']}分, "
                f"完了数: {timing['total_completed_pomos']}回)"
            ),
            inline=False,
        )

        embed.set_footer(text="この分析はあなたの学習パターンに基づいています")
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def award_pomodoro_xp(self, user_id: int, channel: discord.abc.Messageable) -> None:
        """ポモドーロ完了時のXP付与（他Cogから呼び出し）"""
        amount = XP_REWARDS["pomodoro_complete"]
        result = await self.manager.add_xp(user_id, amount, "ポモドーロ完了")
        await self._send_xp_notification(user_id, channel, result)

        # StudyCoin付与
        shop_cog = self.bot.get_cog("ShopCog")
        if shop_cog:
            try:
                await shop_cog.award_coins(
                    user_id, "", COIN_REWARDS["pomodoro_complete"], "ポモドーロ完了"
                )
            except Exception:
                logger.warning("ポモドーロ完了のコイン付与に失敗", exc_info=True)

        # 実績チェック
        ach_cog = self.bot.get_cog("AchievementCog")
        if ach_cog:
            try:
                await ach_cog.check_achievement(user_id, "first_study", 1, channel)
            except Exception:
                logger.warning("実績チェックに失敗", exc_info=True)

        # 連続学習チェック
        streak = await self.manager.check_streak(user_id)
        if streak["bonus"]:
            bonus_result = await self.manager.add_xp(
                user_id, XP_REWARDS["streak_bonus"], "連続学習ボーナス"
            )
            await channel.send(
                embed=xp_embed(
                    f"🔥 連続{streak['streak']}日ボーナス！",
                    f"+{XP_REWARDS['streak_bonus']} XP",
                )
            )
            if bonus_result.get("leveled_up"):
                await self._send_levelup(user_id, channel, bonus_result)

            # 連続学習のコインボーナス
            if shop_cog and streak["streak"] >= 7:
                try:
                    coin_key = "streak_bonus_30" if streak["streak"] >= 30 else "streak_bonus_7"
                    await shop_cog.award_coins(
                        user_id, "", COIN_REWARDS[coin_key], "連続学習ボーナス"
                    )
                except Exception:
                    logger.warning("連続学習コインボーナス付与に失敗", exc_info=True)

            # 連続学習の実績チェック
            if ach_cog:
                try:
                    await ach_cog.check_achievement(user_id, "streak_7", streak["streak"], channel)
                    await ach_cog.check_achievement(user_id, "streak_30", streak["streak"], channel)
                except Exception:
                    logger.warning("連続学習の実績チェックに失敗", exc_info=True)

        # 自己ベストチェック
        await self._check_and_notify_personal_bests(user_id, channel)

        # チームクエスト連携
        await self._update_team_quest(user_id, "team_pomodoro", 1)

        # バディ同時学習ボーナス
        await self._check_buddy_bonus(user_id, channel)

        # バトル貢献
        await self._update_battle_contribution(user_id, "pomodoro", 1)

    async def award_task_xp(
        self, user_id: int, priority: int, channel: discord.abc.Messageable
    ) -> None:
        """タスク完了時のXP付与（他Cogから呼び出し）"""
        reward_key = {1: "task_complete_high", 2: "task_complete_medium", 3: "task_complete_low"}
        key = reward_key.get(priority, "task_complete_low")
        amount = XP_REWARDS.get(key, 10)
        result = await self.manager.add_xp(user_id, amount, "タスク完了")
        await self._send_xp_notification(user_id, channel, result)

        # StudyCoin付与
        shop_cog = self.bot.get_cog("ShopCog")
        if shop_cog:
            try:
                coin_amount = COIN_REWARDS.get(key, 5)
                await shop_cog.award_coins(user_id, "", coin_amount, "タスク完了")
            except Exception:
                logger.warning("タスク完了のコイン付与に失敗", exc_info=True)

        # 実績チェック
        ach_cog = self.bot.get_cog("AchievementCog")
        if ach_cog:
            try:
                await ach_cog.check_achievement(user_id, "first_study", 1, channel)
            except Exception:
                logger.warning("タスク完了の実績チェックに失敗", exc_info=True)

        # チームクエスト連携
        await self._update_team_quest(user_id, "team_tasks", 1)

        # バトル貢献
        await self._update_battle_contribution(user_id, "tasks", 1)

    async def award_study_log_xp(self, user_id: int, channel: discord.abc.Messageable, duration_minutes: int = 0) -> None:
        """学習ログ記録時のXP付与"""
        amount = XP_REWARDS["study_log"]
        result = await self.manager.add_xp(user_id, amount, "学習ログ記録")
        await self._send_xp_notification(user_id, channel, result)

        # StudyCoin付与
        shop_cog = self.bot.get_cog("ShopCog")
        if shop_cog:
            try:
                await shop_cog.award_coins(user_id, "", COIN_REWARDS["study_log"], "学習ログ記録")
            except Exception:
                logger.warning("学習ログのコイン付与に失敗", exc_info=True)

        # 実績チェック
        ach_cog = self.bot.get_cog("AchievementCog")
        if ach_cog:
            try:
                await ach_cog.check_achievement(user_id, "first_study", 1, channel)
            except Exception:
                logger.warning("学習ログの実績チェックに失敗", exc_info=True)

        streak = await self.manager.check_streak(user_id)
        if streak["bonus"]:
            await channel.send(
                embed=xp_embed(
                    f"🔥 連続{streak['streak']}日ボーナス！",
                    f"+{XP_REWARDS['streak_bonus']} XP",
                )
            )

        # 自己ベストチェック
        await self._check_and_notify_personal_bests(user_id, channel)

        # チームクエスト連携
        await self._update_team_quest(user_id, "team_study_minutes", 0)
        # Note: study_minutes delta is handled through study_log duration

        # バトル貢献
        await self._update_battle_contribution(user_id, "study_minutes", duration_minutes)

    async def award_raid_xp(
        self, user_id: int, base_xp: int, channel: discord.abc.Messageable
    ) -> None:
        """レイド完了時のXP付与（XP倍率適用）"""
        multiplied_xp = int(base_xp * RAID_DEFAULTS["xp_multiplier"])
        result = await self.manager.add_xp(user_id, multiplied_xp, "レイド完了")
        await self._send_xp_notification(user_id, channel, result)

    # --- チームクエスト / バディ連携 ---

    async def _update_team_quest(
        self, user_id: int, quest_type: str, delta: int
    ) -> None:
        """チームクエスト進捗を更新"""
        team_cog = self.bot.get_cog("TeamCog")
        if not team_cog:
            return
        try:
            await team_cog.manager.update_team_quest_progress(
                user_id, quest_type, delta
            )
        except Exception:
            logger.debug("チームクエスト更新失敗 (user=%d)", user_id, exc_info=True)

    async def _update_battle_contribution(
        self, user_id: int, goal_type: str, amount: int
    ) -> None:
        """バトル貢献を記録"""
        battle_cog = self.bot.get_cog("BattleCog")
        if not battle_cog:
            return
        try:
            await battle_cog.manager.add_contribution(
                user_id, goal_type, amount, "discord"
            )
        except Exception:
            logger.debug("バトル貢献更新失敗 (user=%d)", user_id, exc_info=True)

    async def _check_buddy_bonus(
        self, user_id: int, channel: discord.abc.Messageable
    ) -> None:
        """バディが同時学習中ならボーナスXPを付与"""
        buddy_cog = self.bot.get_cog("BuddyCog")
        if not buddy_cog:
            return
        try:
            concurrent = await buddy_cog.manager.check_concurrent_session(user_id)
            if concurrent:
                bonus_xp = 10
                result = await self.manager.add_xp(user_id, bonus_xp, "バディ同時学習ボーナス")
                embed = xp_embed(
                    "🤝 バディボーナス！",
                    f"バディと同時に学習中！ +{bonus_xp} XP",
                )
                await channel.send(f"<@{user_id}>", embed=embed)
        except Exception:
            logger.debug("バディボーナスチェック失敗 (user=%d)", user_id, exc_info=True)

    # --- 自己ベスト通知 ---

    async def _check_and_notify_personal_bests(
        self, user_id: int, channel: discord.abc.Messageable
    ) -> None:
        """自己ベスト更新チェック＆祝福通知"""
        try:
            updated = await self.manager.check_personal_bests(user_id)
            if not updated:
                return

            lines = []
            if "best_streak" in updated:
                lines.append(f"🔥 連続学習: **{updated['best_streak']}日**")
            if "best_daily_minutes" in updated:
                lines.append(f"📚 1日の学習時間: **{updated['best_daily_minutes']}分**")
            if "best_weekly_minutes" in updated:
                lines.append(f"📅 週間学習時間: **{updated['best_weekly_minutes']}分**")

            if lines:
                embed = discord.Embed(
                    title="🏆 自己ベスト更新！",
                    description="\n".join(lines),
                    color=COLORS["xp"],
                )
                await channel.send(f"<@{user_id}>", embed=embed)
        except Exception:
            logger.warning("自己ベストチェック失敗 (user=%d)", user_id, exc_info=True)

    async def _send_xp_notification(
        self, user_id: int, channel: discord.abc.Messageable, result: dict
    ) -> None:
        """XP獲得通知を送信"""
        if "error" in result:
            return

        embed = xp_embed(
            f"+{result['xp_gained']} XP",
            f"合計: {result['total_xp']:,} XP | Lv.{result['new_level']}",
        )
        await channel.send(f"<@{user_id}>", embed=embed)

        # シーズンパスXP加算
        try:
            season_result = await self.manager.add_season_xp(
                user_id, result["xp_gained"]
            )
            if season_result and season_result["tier_ups"]:
                for tier_up in season_result["tier_ups"]:
                    await channel.send(
                        embed=xp_embed(
                            f"🏅 シーズンティアアップ！",
                            f"**{tier_up['label']}** に到達！ +{tier_up['reward_coins']} 🪙",
                        )
                    )
                    # コイン付与
                    shop_cog = self.bot.get_cog("ShopCog")
                    if shop_cog:
                        try:
                            await shop_cog.award_coins(
                                user_id, "", tier_up["reward_coins"],
                                f"シーズン報酬: {tier_up['label']}"
                            )
                        except Exception:
                            pass
        except Exception:
            logger.debug("シーズンXP加算失敗 (user=%d)", user_id, exc_info=True)

        # イベント発行: XP獲得
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_xp_gain(
                    user_id=user_id,
                    guild_id=0,
                    username=result.get("username", ""),
                    amount=result.get("xp_gained", 0),
                    reason=result.get("reason", ""),
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

        if result.get("leveled_up"):
            await self._send_levelup(user_id, channel, result)

    async def _send_levelup(
        self, user_id: int, channel: discord.abc.Messageable, result: dict
    ) -> None:
        """レベルアップ通知"""
        milestone = result.get("milestone")
        badge = milestone["badge"] if milestone else "🎉"
        desc = f"**レベル {result['old_level']} → {result['new_level']}**"

        if milestone:
            desc += f"\n\n{milestone['badge']} **{milestone.get('role_name', '')}** の称号を獲得！"
            if milestone.get("description"):
                desc += f"\n_{milestone['description']}_"

        embed = discord.Embed(
            title=f"{badge} レベルアップ！",
            description=desc,
            color=COLORS["xp"],
        )
        await channel.send(f"<@{user_id}>", embed=embed)

        # イベント発行: レベルアップ
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_level_up(
                    user_id=user_id,
                    guild_id=0,
                    username=result.get("username", ""),
                    new_level=result.get("new_level", 0),
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

        # スマホ通知
        nudge_cog = self.bot.get_cog("PhoneNudgeCog")
        if nudge_cog:
            try:
                await nudge_cog.send_nudge(
                    user_id,
                    "level_up",
                    f"🎉 レベルアップ！ Lv.{result['new_level']} に到達しました！",
                )
            except Exception:
                logger.warning("レベルアップ通知の送信に失敗", exc_info=True)

    # --- タスクループ ---

    @tasks.loop(time=time(hour=21, minute=0, tzinfo=JST))
    async def streak_protection_dm(self):
        """毎日21:00 JSTにストリーク保護DMを送信"""
        today = date.today()
        users = await self.manager.repository.get_users_needing_streak_reminder(today)

        for user_data in users:
            try:
                user = self.bot.get_user(user_data["user_id"])
                if not user:
                    try:
                        user = await self.bot.fetch_user(user_data["user_id"])
                    except discord.NotFound:
                        continue

                streak = user_data["streak_days"]

                await user.send(
                    embed=info_embed(
                        "🔥 ストリーク保護リマインダー",
                        f"**{streak}日**連続学習中！今日もあと少し学習して記録を守りましょう！",
                    )
                )
            except discord.Forbidden:
                logger.debug("DM送信不可: user=%d", user_data["user_id"])
            except Exception:
                logger.warning(
                    "ストリーク保護DM送信失敗: user=%d",
                    user_data["user_id"],
                    exc_info=True,
                )

    @streak_protection_dm.before_loop
    async def before_streak_protection_dm(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=time(hour=20, minute=0, tzinfo=JST))
    async def churn_detection_dm(self):
        """毎日20:00 JSTに離脱検知DMを送信"""
        churned = await self.manager.get_churned_users(min_streak=10, inactive_days=2)

        for user_data in churned:
            user_id = user_data["user_id"]
            try:
                # 重複送信防止: 7日以内に送信済みならスキップ
                if await self.nudge_repo.has_recent_churn_dm(user_id, days=7):
                    continue

                user = self.bot.get_user(user_id)
                if not user:
                    try:
                        user = await self.bot.fetch_user(user_id)
                    except discord.NotFound:
                        continue

                best = user_data["best_streak"]
                await user.send(
                    embed=info_embed(
                        "📊 お久しぶりです！",
                        (
                            f"以前 **{best}日**連続で頑張っていました！\n"
                            "また一緒に学習を始めませんか？\n\n"
                            "💡 `/pomodoro start` でいつでも再開できます。\n"
                            "少しずつでも続けることが大切です！"
                        ),
                    )
                )

                # 送信記録
                await self.nudge_repo.record_churn_dm(user_id)

            except discord.Forbidden:
                logger.debug("離脱検知DM送信不可: user=%d", user_id)
            except Exception:
                logger.warning(
                    "離脱検知DM送信失敗: user=%d", user_id, exc_info=True
                )

    @churn_detection_dm.before_loop
    async def before_churn_detection_dm(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = GamificationManager(db_pool)
    await bot.add_cog(GamificationCog(bot, manager))
