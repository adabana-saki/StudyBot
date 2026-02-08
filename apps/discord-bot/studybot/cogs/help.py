"""ヘルプ Cog

カテゴリ別コマンド一覧を表示するインタラクティブヘルプメニューを提供する。
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from studybot.config.constants import HELP_CATEGORIES
from studybot.utils.embed_helper import help_embed

logger = logging.getLogger(__name__)

COMMAND_HELP = {
    "study": [
        ("/pomodoro start [topic] [work_min] [break_min]", "ポモドーロセッションを開始"),
        ("/pomodoro pause", "セッションを一時停止"),
        ("/pomodoro resume", "セッションを再開"),
        ("/pomodoro stop", "セッションを停止"),
        ("/pomodoro status", "タイマーの状態を確認"),
        ("/study log [duration] [topic]", "学習時間を記録"),
        ("/study stats [period]", "学習統計を表示"),
        ("/study chart [type] [days]", "学習チャートを生成"),
        ("/todo add", "タスクを追加（モーダル）"),
        ("/todo quick [title]", "タスクをすばやく追加"),
        ("/todo list [status]", "タスク一覧を表示"),
        ("/todo complete [id]", "タスクを完了"),
        ("/todo delete [id]", "タスクを削除"),
        ("/focus start [duration]", "フォーカスモードを開始"),
        ("/focus end", "フォーカスモードを終了"),
        ("/focus whitelist [channel]", "ホワイトリストにチャンネル追加"),
        ("/vc status", "現在VCで勉強中のメンバー一覧"),
        ("/vc stats [days]", "VC勉強時間統計"),
    ],
    "gamification": [
        ("/profile", "自分のプロフィールを表示"),
        ("/profile edit", "プロフィールを編集"),
        ("/profile [user]", "他ユーザーのプロフィール閲覧"),
        ("/xp", "現在のXPとレベルを表示"),
        ("/leaderboard [category]", "リーダーボードを表示"),
        ("/shop list [category]", "ショップのアイテム一覧"),
        ("/shop buy [id]", "アイテムを購入"),
        ("/shop inventory", "所持アイテムを表示"),
        ("/shop equip [item]", "アイテムを装備/使用"),
        ("/shop roles", "取得可能な特別ロール一覧"),
        ("/coins", "StudyCoinの残高を表示"),
        ("/achievements", "実績一覧を表示"),
        ("/raid create [topic] [duration]", "スタディレイドを作成"),
        ("/raid join [id]", "レイドに参加"),
        ("/raid status", "アクティブなレイド一覧"),
    ],
    "ai": [
        ("/ai summarize", "ドキュメントをAI要約"),
        ("/flashcard create [deck]", "フラッシュカードデッキを作成"),
        ("/flashcard review [deck]", "フラッシュカードを復習"),
        ("/flashcard list", "デッキ一覧を表示"),
        ("/plan create [subject] [goal]", "AI学習プランを生成"),
        ("/plan list", "学習プラン一覧"),
    ],
    "wellness": [
        ("/wellness log [mood] [energy] [stress]", "ウェルネスを記録"),
        ("/wellness stats [days]", "ウェルネス統計を表示"),
        ("/wellness chart [days]", "ウェルネスチャートを生成"),
        ("/nudge setup [url]", "Webhook URLを設定"),
        ("/nudge toggle [enabled]", "通知のON/OFF切り替え"),
        ("/nudge lock [duration]", "フォーカスロックを開始"),
        ("/nudge shield [duration]", "フォーカスシールドを開始"),
    ],
    "settings": [
        ("/admin grant_xp [user] [amount]", "XPを付与（管理者）"),
        ("/admin grant_coins [user] [amount]", "コインを付与（管理者）"),
        ("/admin server_stats", "サーバー全体統計"),
        ("/admin set_study_channel [channel]", "勉強チャンネルを設定"),
        ("/admin set_vc_channel [channel]", "VC追跡チャンネルを設定"),
        ("/help", "このヘルプを表示"),
    ],
}


class HelpCategorySelect(discord.ui.Select):
    """ヘルプカテゴリ選択メニュー"""

    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=label, value=key, description=f"{key}関連のコマンド")
            for key, label in HELP_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="カテゴリを選択...",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        category = self.values[0]
        label = HELP_CATEGORIES.get(category, category)
        commands_list = COMMAND_HELP.get(category, [])

        lines = []
        for cmd, desc in commands_list:
            lines.append(f"`{cmd}`\n　{desc}")

        embed = help_embed(
            f"ヘルプ - {label}",
            "\n\n".join(lines) if lines else "コマンドがありません。",
        )
        embed.set_footer(text="カテゴリを選択して他のコマンドを表示")
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    """ヘルプビュー"""

    def __init__(self) -> None:
        super().__init__(timeout=300)
        self.add_item(HelpCategorySelect())


class HelpCog(commands.Cog):
    """ヘルプ機能"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="StudyBotのヘルプを表示")
    async def help_command(self, interaction: discord.Interaction) -> None:
        categories = []
        for key, label in HELP_CATEGORIES.items():
            count = len(COMMAND_HELP.get(key, []))
            categories.append(f"{label} ({count}コマンド)")

        embed = help_embed(
            "StudyBot ヘルプ",
            (
                "StudyBotは学習支援のためのDiscord Botです。\n"
                "以下のカテゴリから表示したいコマンドを選択してください。\n\n"
                + "\n".join(categories)
            ),
        )
        embed.set_footer(text="下のメニューからカテゴリを選択")
        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    """HelpCogをBotに登録する。"""
    await bot.add_cog(HelpCog(bot))
