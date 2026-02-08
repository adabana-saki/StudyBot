"""スマホ通知 Cog"""

import logging
import random
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from studybot.config.constants import COIN_REWARDS, COLORS, NUDGE_LEVELS, UNLOCK_LEVELS
from studybot.managers.nudge_manager import NudgeManager
from studybot.utils.embed_helper import error_embed, focus_embed, success_embed

logger = logging.getLogger(__name__)

ENCOURAGEMENT_MESSAGES = [
    "頑張っています！集中を続けましょう！",
    "素晴らしい集中力です！",
    "あと少しです、ファイト！",
    "集中モード継続中！その調子です！",
    "スマホを置いて、目標に集中しましょう！",
]


class LockConfirmView(discord.ui.View):
    """ロック開始確認ビュー"""

    def __init__(
        self,
        manager: NudgeManager,
        user_id: int,
        username: str,
        lock_type: str,
        duration: int,
        coins_bet: int = 0,
        unlock_level: int = 1,
    ) -> None:
        super().__init__(timeout=60)
        self.manager = manager
        self.user_id = user_id
        self.username = username
        self.lock_type = lock_type
        self.duration = duration
        self.coins_bet = coins_bet
        self.unlock_level = unlock_level

    @discord.ui.button(label="ロック開始", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=error_embed("エラー", "この操作は実行できません。"),
                ephemeral=True,
            )
            return

        if self.lock_type == "shield":
            result = await self.manager.start_shield(self.user_id, self.username, self.duration)
        else:
            result = await self.manager.start_lock(
                self.user_id,
                self.username,
                self.duration,
                self.coins_bet,
                self.unlock_level,
            )

        if "error" in result:
            await interaction.response.edit_message(
                embed=error_embed("ロック開始エラー", result["error"]),
                view=None,
            )
            return

        level_name = (
            NUDGE_LEVELS[self.lock_type]["name"]
            if self.lock_type in NUDGE_LEVELS
            else "フォーカスロック"
        )
        desc = f"**{level_name}**を開始しました！\n"
        desc += f"時間: **{self.duration}分**\n"
        if self.unlock_level > 1:
            ul = UNLOCK_LEVELS.get(self.unlock_level, {})
            desc += f"アンロックレベル: **Lv{self.unlock_level} ({ul.get('name', '')})**\n"
        if self.coins_bet > 0:
            desc += f"ベットコイン: **{self.coins_bet}枚**\n"

        # レベル2: 確認コードをDM送信
        if self.unlock_level == 2 and result.get("confirmation_code"):
            try:
                user = interaction.user
                await user.send(
                    f"🔒 フォーカスロック確認コード: **{result['confirmation_code']}**\n"
                    f"このコードは解除時に必要です（有効期限: 15分）"
                )
                desc += "\n確認コードをDMに送信しました。"
            except discord.Forbidden:
                desc += "\n⚠️ DMの送信に失敗しました。DM設定を確認してください。"

        desc += "\n集中して頑張りましょう！"

        embed = focus_embed("ロック開始", desc)
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)

        # イベント発行: ロック開始
        bot = interaction.client
        if hasattr(bot, "event_publisher") and bot.event_publisher:
            try:
                await bot.event_publisher.emit_lock_start(
                    user_id=self.user_id,
                    guild_id=getattr(interaction, "guild_id", 0) or 0,
                    username=self.username,
                    duration_minutes=self.duration,
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=error_embed("エラー", "この操作は実行できません。"),
                ephemeral=True,
            )
            return

        self.stop()
        await interaction.response.edit_message(
            embed=focus_embed("キャンセル", "ロックをキャンセルしました。"),
            view=None,
        )


class BreakConfirmView(discord.ui.View):
    """ロック中断確認ビュー"""

    def __init__(self, manager: NudgeManager, user_id: int, coins_bet: int) -> None:
        super().__init__(timeout=60)
        self.manager = manager
        self.user_id = user_id
        self.coins_bet = coins_bet

    @discord.ui.button(label="ロック解除", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=error_embed("エラー", "この操作は実行できません。"),
                ephemeral=True,
            )
            return

        result = await self.manager.break_lock(self.user_id)
        if "error" in result:
            await interaction.response.edit_message(
                embed=error_embed("エラー", result["error"]),
                view=None,
            )
            return

        desc = "ロックを解除しました。\n"
        if result.get("coins_lost", 0) > 0:
            desc += f"ベットしたコイン **{result['coins_lost']}枚** を失いました。"
        else:
            desc += "次回は最後まで頑張りましょう！"

        self.stop()
        await interaction.response.edit_message(
            embed=error_embed("ロック解除", desc),
            view=None,
        )

        # イベント発行: ロック終了（手動解除）
        bot = interaction.client
        if hasattr(bot, "event_publisher") and bot.event_publisher:
            try:
                await bot.event_publisher.emit_lock_end(
                    user_id=self.user_id,
                    guild_id=getattr(interaction, "guild_id", 0) or 0,
                    username=interaction.user.display_name,
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                embed=error_embed("エラー", "この操作は実行できません。"),
                ephemeral=True,
            )
            return

        self.stop()
        await interaction.response.edit_message(
            embed=focus_embed("キャンセル", "ロック解除をキャンセルしました。"),
            view=None,
        )


class PhoneNudgeCog(commands.Cog):
    """スマホ通知機能"""

    def __init__(self, bot: commands.Bot, manager: NudgeManager) -> None:
        self.bot = bot
        self.manager = manager
        self.lock_check.start()

    def cog_unload(self) -> None:
        self.lock_check.cancel()

    nudge_group = app_commands.Group(name="nudge", description="スマホ通知設定")

    @nudge_group.command(name="setup", description="Webhook URLを設定")
    @app_commands.describe(webhook_url="通知先のWebhook URL")
    async def nudge_setup(self, interaction: discord.Interaction, webhook_url: str):
        result = await self.manager.setup_webhook(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            webhook_url=webhook_url,
        )

        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("設定エラー", result["error"]),
                ephemeral=True,
            )
            return

        embed = success_embed(
            "通知設定完了",
            "Webhook URLが設定されました。\n学習開始やレベルアップ時に通知が届きます。",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nudge_group.command(name="toggle", description="通知のON/OFF切り替え")
    @app_commands.describe(enabled="通知を有効にするか")
    async def nudge_toggle(self, interaction: discord.Interaction, enabled: bool):
        success = await self.manager.toggle(interaction.user.id, enabled)
        if not success:
            await interaction.response.send_message(
                embed=error_embed("エラー", "まず /nudge setup で設定してください。"),
                ephemeral=True,
            )
            return

        status = "有効" if enabled else "無効"
        await interaction.response.send_message(
            embed=success_embed("通知設定", f"通知を**{status}**にしました。"),
            ephemeral=True,
        )

    @nudge_group.command(name="test", description="テスト通知を送信")
    async def nudge_test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        success = await self.manager.send_nudge(
            interaction.user.id,
            "test",
            "StudyBot テスト通知です！",
        )

        if success:
            await interaction.followup.send(
                embed=success_embed("テスト成功", "通知が送信されました！"),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                embed=error_embed(
                    "テスト失敗",
                    "通知の送信に失敗しました。\nWebhook URLが正しいか確認してください。",
                ),
                ephemeral=True,
            )

    @nudge_group.command(name="status", description="現在の通知設定を表示")
    async def nudge_status(self, interaction: discord.Interaction):
        config = await self.manager.get_config(interaction.user.id)

        if not config:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="通知設定",
                    description="未設定です。`/nudge setup` で設定してください。",
                    color=COLORS["primary"],
                ),
                ephemeral=True,
            )
            return

        status = "有効" if config.get("enabled") else "無効"
        url = config.get("webhook_url", "")
        masked_url = url[:30] + "..." if len(url) > 30 else url

        embed = discord.Embed(
            title="通知設定",
            color=COLORS["primary"],
        )
        embed.add_field(name="ステータス", value=status, inline=True)
        embed.add_field(name="Webhook", value=masked_url, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def send_nudge(self, user_id: int, event_type: str, message: str) -> None:
        """他Cogから呼び出し用の通知メソッド"""
        await self.manager.send_nudge(user_id, event_type, message)

    async def on_study_completed(self, user_id: int) -> None:
        """学習完了時のフック（レベル4ロック用）"""
        code = await self.manager.on_study_completed(user_id)
        if code:
            try:
                user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                if user:
                    await user.send(
                        f"📚 学習完了！フォーカスロック解除コード: **{code}**\n（有効期限: 15分）"
                    )
            except Exception as e:
                logger.warning("学習完了コード送信エラー (user=%d): %s", user_id, e)

    @nudge_group.command(name="lock", description="フォーカスロックを開始（コインベット可能）")
    @app_commands.describe(
        duration="ロック時間（分）",
        coins_bet="ベットするコイン数（任意、10〜100）",
        unlock_level="アンロックレベル（1〜5）",
    )
    @app_commands.choices(
        unlock_level=[
            app_commands.Choice(name="Lv1: タイマー完了", value=1),
            app_commands.Choice(name="Lv2: 確認コード", value=2),
            app_commands.Choice(name="Lv3: DMコード", value=3),
            app_commands.Choice(name="Lv4: 学習完了コード", value=4),
            app_commands.Choice(name="Lv5: ペナルティ解除", value=5),
        ]
    )
    async def nudge_lock(
        self,
        interaction: discord.Interaction,
        duration: int,
        coins_bet: int = 0,
        unlock_level: int = 1,
    ):
        if duration <= 0:
            await interaction.response.send_message(
                embed=error_embed("エラー", "ロック時間は1分以上を指定してください。"),
                ephemeral=True,
            )
            return

        lock_config = NUDGE_LEVELS["lock"]
        ul = UNLOCK_LEVELS.get(unlock_level, UNLOCK_LEVELS[1])
        desc = f"**{lock_config['name']}**を開始しますか？\n"
        desc += f"時間: **{duration}分**\n"
        desc += f"アンロックレベル: **Lv{unlock_level} ({ul['name']})**\n"
        desc += f"_{ul['description']}_\n"
        if coins_bet > 0:
            desc += f"ベットコイン: **{coins_bet}枚**\n"
            desc += "（途中解除するとベットコインを失います）\n"
        desc += f"\n完了報酬: **{COIN_REWARDS['lock_complete']}コイン**"
        if coins_bet > 0:
            desc += f" + ベット返還 **{coins_bet}コイン**"

        embed = focus_embed("フォーカスロック確認", desc)
        view = LockConfirmView(
            self.manager,
            interaction.user.id,
            interaction.user.display_name,
            "lock",
            duration,
            coins_bet,
            unlock_level,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @nudge_group.command(name="shield", description="フォーカスシールドを開始（最大制限モード）")
    @app_commands.describe(duration="シールド時間（分、30〜240）")
    async def nudge_shield(self, interaction: discord.Interaction, duration: int):
        shield_config = NUDGE_LEVELS["shield"]
        if duration < shield_config["min_duration"] or duration > shield_config["max_duration"]:
            await interaction.response.send_message(
                embed=error_embed(
                    "エラー",
                    f"シールド時間は{shield_config['min_duration']}〜"
                    f"{shield_config['max_duration']}分の範囲で指定してください。",
                ),
                ephemeral=True,
            )
            return

        desc = f"**{shield_config['name']}**を開始しますか？\n"
        desc += f"時間: **{duration}分**\n"
        desc += f"（{shield_config['nudge_interval_minutes']}分ごとに励ましメッセージが届きます）\n"
        desc += f"\n完了報酬: **{COIN_REWARDS['lock_complete']}コイン**"

        embed = focus_embed("フォーカスシールド確認", desc)
        view = LockConfirmView(
            self.manager,
            interaction.user.id,
            interaction.user.display_name,
            "shield",
            duration,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @nudge_group.command(name="break_lock", description="現在のロックを解除")
    async def nudge_break_lock(self, interaction: discord.Interaction):
        status = await self.manager.get_lock_status(interaction.user.id)
        if not status:
            await interaction.response.send_message(
                embed=error_embed("エラー", "アクティブなロックがありません。"),
                ephemeral=True,
            )
            return

        coins_bet = status.get("coins_bet", 0)
        remaining = status.get("remaining_minutes", 0)

        desc = f"残り **{remaining}分** のロックを解除しますか？\n"
        if coins_bet > 0:
            desc += f"ベットしたコイン **{coins_bet}枚** を失います。"
        else:
            desc += "本当に解除しますか？"

        embed = focus_embed("ロック解除確認", desc)
        view = BreakConfirmView(self.manager, interaction.user.id, coins_bet)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @nudge_group.command(name="lock_status", description="現在のロックステータスを表示")
    async def nudge_lock_status(self, interaction: discord.Interaction):
        status = await self.manager.get_lock_status(interaction.user.id)
        if not status:
            await interaction.response.send_message(
                embed=focus_embed(
                    "ロックステータス",
                    "現在アクティブなロックはありません。",
                ),
                ephemeral=True,
            )
            return

        lock_type = status.get("lock_type", "lock")
        level_name = NUDGE_LEVELS.get(lock_type, {}).get("name", "フォーカスロック")
        remaining_min = status["remaining_minutes"]
        remaining_sec = status["remaining_seconds"] % 60
        unlock_level = status.get("unlock_level", 1)
        ul = UNLOCK_LEVELS.get(unlock_level, UNLOCK_LEVELS[1])

        desc = f"**{level_name}** が有効です\n\n"
        desc += f"残り時間: **{remaining_min}分{remaining_sec}秒**\n"
        desc += f"アンロックレベル: **Lv{unlock_level} ({ul['name']})**\n"
        if status.get("coins_bet", 0) > 0:
            desc += f"ベットコイン: **{status['coins_bet']}枚**\n"

        embed = focus_embed("ロックステータス", desc)
        embed.color = COLORS["focus"]
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nudge_group.command(name="code", description="ロック解除コードを入力")
    @app_commands.describe(code="解除コード")
    async def nudge_code(self, interaction: discord.Interaction, code: str):
        """コード入力でロック解除"""
        result = await self.manager.verify_unlock_code(interaction.user.id, code)

        if "error" in result:
            await interaction.response.send_message(
                embed=error_embed("コード検証エラー", result["error"]),
                ephemeral=True,
            )
            return

        desc = "コード検証成功！ロックを解除しました。\n"
        coins_earned = result.get("coins_earned", 0)
        coins_returned = result.get("coins_returned", 0)
        if coins_earned > 0:
            desc += f"獲得コイン: **{coins_earned}枚**\n"
        if coins_returned > 0:
            desc += f"ベット返還: **{coins_returned}枚**\n"

        # コイン付与
        total_coins = coins_earned + coins_returned
        if total_coins > 0:
            shop_cog = self.bot.get_cog("ShopCog")
            if shop_cog:
                try:
                    await shop_cog.award_coins(
                        interaction.user.id, "", total_coins, "フォーカスロック完了"
                    )
                except Exception as e:
                    logger.warning("コイン付与エラー (user=%d): %s", interaction.user.id, e)

        await interaction.response.send_message(
            embed=success_embed("ロック解除", desc),
            ephemeral=True,
        )

        # イベント発行: ロック終了（コード解除）
        if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
            try:
                await self.bot.event_publisher.emit_lock_end(
                    user_id=interaction.user.id,
                    guild_id=getattr(interaction, "guild_id", 0) or 0,
                    username=interaction.user.display_name,
                )
            except Exception:
                logger.warning("イベント発行失敗", exc_info=True)

    @nudge_group.command(name="settings", description="デフォルトロック設定を変更")
    @app_commands.describe(
        unlock_level="デフォルトアンロックレベル（1〜5）",
        duration="デフォルトロック時間（分）",
        coin_bet="デフォルトベットコイン数",
    )
    async def nudge_settings(
        self,
        interaction: discord.Interaction,
        unlock_level: int | None = None,
        duration: int | None = None,
        coin_bet: int | None = None,
    ):
        """デフォルトロック設定を表示/変更"""
        settings = await self.manager.lock_settings_repo.get_settings(interaction.user.id)

        if unlock_level is None and duration is None and coin_bet is None:
            # 設定表示
            if not settings:
                desc = "デフォルト設定は未登録です。\n引数を指定して設定してください。"
            else:
                ul = UNLOCK_LEVELS.get(settings["default_unlock_level"], UNLOCK_LEVELS[1])
                desc = (
                    f"アンロックレベル: **Lv{settings['default_unlock_level']}"
                    f" ({ul['name']})**\n"
                    f"ロック時間: **{settings['default_duration']}分**\n"
                    f"ベットコイン: **{settings['default_coin_bet']}枚**\n"
                )
                if settings.get("block_categories"):
                    desc += f"ブロックカテゴリ: {', '.join(settings['block_categories'])}\n"
            await interaction.response.send_message(
                embed=focus_embed("ロック設定", desc),
                ephemeral=True,
            )
            return

        # 設定更新
        current = settings or {
            "default_unlock_level": 1,
            "default_duration": 60,
            "default_coin_bet": 0,
            "block_categories": [],
            "custom_blocked_urls": [],
        }

        new_level = unlock_level if unlock_level is not None else current["default_unlock_level"]
        new_duration = duration if duration is not None else current["default_duration"]
        new_bet = coin_bet if coin_bet is not None else current["default_coin_bet"]

        if new_level < 1 or new_level > 5:
            await interaction.response.send_message(
                embed=error_embed("エラー", "アンロックレベルは1〜5の範囲で指定してください。"),
                ephemeral=True,
            )
            return

        await self.manager.lock_settings_repo.upsert_settings(
            user_id=interaction.user.id,
            default_unlock_level=new_level,
            default_duration=new_duration,
            default_coin_bet=new_bet,
            block_categories=current.get("block_categories", []),
            custom_blocked_urls=current.get("custom_blocked_urls", []),
        )

        ul = UNLOCK_LEVELS.get(new_level, UNLOCK_LEVELS[1])
        desc = (
            f"アンロックレベル: **Lv{new_level} ({ul['name']})**\n"
            f"ロック時間: **{new_duration}分**\n"
            f"ベットコイン: **{new_bet}枚**\n"
        )
        await interaction.response.send_message(
            embed=success_embed("ロック設定を更新", desc),
            ephemeral=True,
        )

    @tasks.loop(seconds=30)
    async def lock_check(self):
        """アクティブロックの期限チェックと定期ナッジ"""
        try:
            # シールドモードの定期ナッジ送信
            now = datetime.now(UTC)
            nudge_interval = NUDGE_LEVELS["shield"]["nudge_interval_minutes"]
            for user_id, info in list(self.manager.active_locks.items()):
                if info.get("lock_type") == "shield":
                    last_nudge = info.get("last_nudge_time", now)
                    if (now - last_nudge).total_seconds() >= nudge_interval * 60:
                        message = random.choice(ENCOURAGEMENT_MESSAGES)
                        await self.manager.send_nudge(user_id, "shield_nudge", message)
                        info["last_nudge_time"] = now

            # コードリクエストの処理
            await self.manager.process_code_requests(self.bot)

            # 期限切れロックの完了処理（レベル1のみ自動完了）
            completed = await self.manager.check_locks()
            for result in completed:
                user_id = result.get("user_id")
                if not user_id:
                    continue

                # ShopCogでコイン付与
                coins_earned = result.get("coins_earned", 0)
                coins_returned = result.get("coins_returned", 0)
                total_coins = coins_earned + coins_returned

                if total_coins > 0:
                    shop_cog = self.bot.get_cog("ShopCog")
                    if shop_cog:
                        try:
                            await shop_cog.award_coins(
                                user_id, "", total_coins, "フォーカスロック完了"
                            )
                        except Exception as e:
                            logger.warning("コイン付与エラー (user=%d): %s", user_id, e)

                # イベント発行: ロック終了（自動完了）
                if hasattr(self.bot, "event_publisher") and self.bot.event_publisher:
                    try:
                        await self.bot.event_publisher.emit_lock_end(
                            user_id=user_id,
                            guild_id=0,
                            username="",
                        )
                    except Exception:
                        logger.warning("イベント発行失敗", exc_info=True)

                # 完了通知を送信
                desc = "フォーカスロックが完了しました！\n"
                desc += f"獲得コイン: **{coins_earned}枚**"
                if coins_returned > 0:
                    desc += f"\nベット返還: **{coins_returned}枚**"
                await self.manager.send_nudge(user_id, "lock_complete", desc)

        except Exception as e:
            logger.error("ロックチェックエラー: %s", e)

    @lock_check.before_loop
    async def before_lock_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db_pool = getattr(bot, "db_pool", None)
    if not db_pool:
        logger.error("db_pool が見つかりません")
        return
    manager = NudgeManager(db_pool)
    await bot.add_cog(PhoneNudgeCog(bot, manager))
