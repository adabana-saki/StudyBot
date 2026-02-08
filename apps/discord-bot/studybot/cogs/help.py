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
        ("/focus status", "フォーカスの状態を確認"),
        ("/vc status", "現在VCで勉強中のメンバー一覧"),
        ("/vc stats [days]", "VC勉強時間統計"),
    ],
    "gamification": [
        ("/profile [user]", "プロフィールを表示"),
        ("/profile_edit", "プロフィールを編集"),
        ("/xp", "現在のXPとレベルを表示"),
        ("/streak", "連続学習の詳細を表示"),
        ("/leaderboard [category] [period]", "ランキングを表示"),
        ("/shop list [category]", "ショップのアイテム一覧"),
        ("/shop buy [id]", "アイテムを購入"),
        ("/shop inventory", "所持アイテムを表示"),
        ("/shop equip [item]", "アイテムを装備/使用"),
        ("/shop roles", "取得可能な特別ロール一覧"),
        ("/coins", "StudyCoinの残高を表示"),
        ("/achievements list", "全実績の一覧を表示"),
        ("/achievements progress", "自分の実績進捗を表示"),
        ("/quest daily", "今日のデイリークエストを表示"),
        ("/quest claim [quest_id]", "クエスト報酬を受け取る"),
    ],
    "social": [
        ("/raid create [topic] [duration]", "スタディレイドを作成"),
        ("/raid join [id]", "レイドに参加"),
        ("/raid leave [id]", "レイドから離脱"),
        ("/raid status", "アクティブなレイド一覧"),
        ("/team create [name]", "スタディチームを作成"),
        ("/team join [id]", "チームに参加"),
        ("/team leave [id]", "チームから脱退"),
        ("/team list", "サーバーのチーム一覧"),
        ("/team stats [id]", "チーム統計を表示"),
        ("/team members [id]", "チームメンバーを表示"),
        ("/buddy find [subject]", "スタディバディを探す"),
        ("/buddy status", "バディマッチ状況を確認"),
        ("/buddy history", "バディマッチ履歴"),
        ("/buddy profile", "バディプロフィール設定"),
        ("/challenge create [name] [duration]", "チャレンジを作成"),
        ("/challenge join [id]", "チャレンジに参加"),
        ("/challenge checkin [id]", "今日のチェックイン"),
        ("/challenge list", "チャレンジ一覧"),
        ("/challenge leaderboard [id]", "チャレンジランキング"),
    ],
    "ai": [
        ("/ai summarize [file]", "ファイルをAIで要約"),
        ("/ai keypoints [file]", "キーポイントを抽出"),
        ("/ai quiz [file] [count]", "クイズを生成"),
        ("/ai ask [file] [question]", "ファイルについて質問"),
        ("/ai explain [concept]", "概念をAIで解説"),
        ("/flashcard create [topic]", "フラッシュカードを作成"),
        ("/flashcard study [topic]", "フラッシュカードで学習"),
        ("/flashcard stats", "フラッシュカード統計"),
        ("/plan create [subject] [goal]", "AI学習プランを生成"),
        ("/plan view", "学習プランを表示"),
        ("/plan progress", "プラン進捗を表示"),
        ("/plan complete [task_id]", "プランのタスクを完了"),
        ("/path list [category]", "ラーニングパス一覧"),
        ("/path enroll [path_id]", "ラーニングパスに登録"),
        ("/path progress [path_id]", "パス進捗を表示"),
        ("/path complete [path_id]", "マイルストーンを完了"),
        ("/insights preview", "今週のAIインサイトをプレビュー"),
    ],
    "wellness": [
        ("/wellness check", "ウェルネスを記録（モーダル）"),
        ("/wellness stats", "ウェルネス統計を表示"),
        ("/nudge setup [url]", "Webhook URLを設定"),
        ("/nudge toggle [enabled]", "通知のON/OFF切り替え"),
        ("/nudge test", "テスト通知を送信"),
        ("/nudge status", "通知設定を表示"),
        ("/nudge lock [duration]", "フォーカスロックを開始"),
        ("/nudge shield [duration]", "フォーカスシールドを開始"),
        ("/nudge break_lock", "ロックを解除"),
        ("/nudge lock_status", "ロックステータスを表示"),
        ("/nudge code [code]", "解除コードを入力"),
        ("/nudge settings", "デフォルトロック設定を変更"),
    ],
    "settings": [
        ("/admin grant_xp [user] [amount]", "XPを付与（管理者）"),
        ("/admin grant_coins [user] [amount]", "コインを付与（管理者）"),
        ("/admin reset_user [user]", "ユーザーデータをリセット（管理者）"),
        ("/admin server_stats", "サーバー全体統計"),
        ("/admin set_study_channel [channel]", "勉強チャンネルを設定"),
        ("/admin set_vc_channel [channel]", "VC追跡チャンネルを設定"),
        ("/help", "このヘルプを表示"),
    ],
}


class HelpCategorySelect(discord.ui.Select):
    """ヘルプカテゴリ選択メニュー"""

    def __init__(self) -> None:
        descriptions = {
            "study": "ポモドーロ・学習ログ・To-Do・フォーカス",
            "gamification": "XP・ショップ・実績・クエスト",
            "social": "レイド・チーム・バディ・チャレンジ",
            "ai": "AI要約・クイズ・プラン・パス",
            "wellness": "ウェルネス・通知・ロック",
            "settings": "管理者コマンド・ヘルプ",
        }
        options = [
            discord.SelectOption(
                label=label,
                value=key,
                description=descriptions.get(key, f"{key}関連のコマンド"),
            )
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
