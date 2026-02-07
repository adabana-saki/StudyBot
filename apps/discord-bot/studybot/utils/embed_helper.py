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
