"""Embed生成ヘルパー"""

import discord

from studybot.config.constants import COLORS


def success_embed(title: str, description: str = "") -> discord.Embed:
    """成功Embed"""
    return discord.Embed(title=f"✅ {title}", description=description, color=COLORS["success"])


def error_embed(title: str, description: str = "") -> discord.Embed:
    """エラーEmbed"""
    return discord.Embed(title=f"❌ {title}", description=description, color=COLORS["error"])


def info_embed(title: str, description: str = "") -> discord.Embed:
    """情報Embed"""
    return discord.Embed(title=title, description=description, color=COLORS["primary"])


def study_embed(title: str, description: str = "") -> discord.Embed:
    """学習関連Embed"""
    return discord.Embed(title=title, description=description, color=COLORS["study"])


def xp_embed(title: str, description: str = "") -> discord.Embed:
    """XP関連Embed"""
    return discord.Embed(title=title, description=description, color=COLORS["xp"])


def coin_embed(title: str, description: str = "") -> discord.Embed:
    """StudyCoin関連Embed"""
    return discord.Embed(title=f"🪙 {title}", description=description, color=COLORS["coins"])


def raid_embed(title: str, description: str = "") -> discord.Embed:
    """スタディレイドEmbed"""
    return discord.Embed(title=f"⚔️ {title}", description=description, color=COLORS["raid"])


def wellness_embed(title: str, description: str = "") -> discord.Embed:
    """ウェルネスEmbed"""
    return discord.Embed(title=f"🧘 {title}", description=description, color=COLORS["wellness"])


def achievement_embed(title: str, description: str = "") -> discord.Embed:
    """実績Embed"""
    return discord.Embed(title=f"🏆 {title}", description=description, color=COLORS["achievement"])


def focus_embed(title: str, description: str = "") -> discord.Embed:
    """フォーカスEmbed"""
    return discord.Embed(title=f"🎯 {title}", description=description, color=COLORS["focus"])


def help_embed(title: str, description: str = "") -> discord.Embed:
    """ヘルプEmbed"""
    return discord.Embed(title=f"📖 {title}", description=description, color=COLORS["primary"])


def admin_embed(title: str, description: str = "") -> discord.Embed:
    """管理者Embed"""
    return discord.Embed(title=f"🔧 {title}", description=description, color=COLORS["warning"])


def vc_embed(title: str, description: str = "") -> discord.Embed:
    """VC勉強Embed"""
    return discord.Embed(title=f"🎙️ {title}", description=description, color=COLORS["study"])


def buddy_embed(title: str, description: str = "") -> discord.Embed:
    """バディEmbed"""
    return discord.Embed(title=f"🤝 {title}", description=description, color=COLORS["buddy"])


def insights_embed(title: str, description: str = "") -> discord.Embed:
    """インサイトEmbed"""
    return discord.Embed(title=f"🧠 {title}", description=description, color=COLORS["insights"])


def challenge_embed(title: str, description: str = "") -> discord.Embed:
    """チャレンジEmbed"""
    return discord.Embed(title=f"🏅 {title}", description=description, color=COLORS["challenge"])


def quest_embed(title: str, description: str = "") -> discord.Embed:
    """クエストEmbed"""
    return discord.Embed(title=f"📋 {title}", description=description, color=COLORS["quest"])


def team_embed(title: str, description: str = "") -> discord.Embed:
    """チームEmbed"""
    return discord.Embed(title=f"👥 {title}", description=description, color=COLORS["team"])


def path_embed(title: str, description: str = "") -> discord.Embed:
    """ラーニングパスEmbed"""
    return discord.Embed(
        title=f"📚 {title}", description=description, color=COLORS["learning_path"]
    )


def sanctuary_embed(title: str, description: str = "") -> discord.Embed:
    """サンクチュアリEmbed"""
    return discord.Embed(title=f"🌿 {title}", description=description, color=COLORS["sanctuary"])


def expedition_embed(title: str, description: str = "") -> discord.Embed:
    """エクスペディションEmbed"""
    return discord.Embed(title=f"🗺️ {title}", description=description, color=COLORS["expedition"])


def forge_embed(title: str, description: str = "") -> discord.Embed:
    """フォージEmbed"""
    return discord.Embed(title=f"🔨 {title}", description=description, color=COLORS["forge"])
