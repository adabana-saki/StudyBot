"""StudyBot - AI搭載学習支援Discord Bot"""

import asyncio
import logging
import sys

import discord
from discord.ext import commands

from studybot.config.settings import settings
from studybot.database.manager import DatabaseManager

# ログ設定
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("studybot")


class StudyBot(commands.Bot):
    """学習支援Discord Bot"""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents)
        self.db_manager = DatabaseManager()

    async def setup_hook(self) -> None:
        """Bot接続前の初期化"""
        # データベース初期化
        if not await self.db_manager.initialize():
            logger.error("データベース初期化に失敗しました")
            return

        self.db_pool = self.db_manager.pool

        # Cog読み込み
        cogs = [
            "studybot.cogs.pomodoro",
            "studybot.cogs.study_log",
            "studybot.cogs.todo",
            "studybot.cogs.gamification",
            "studybot.cogs.leaderboard",
            "studybot.cogs.ai_doc",
            "studybot.cogs.phone_nudge",
            # Phase 2
            "studybot.cogs.shop",
            "studybot.cogs.raid",
            "studybot.cogs.achievement",
            "studybot.cogs.flashcard",
            "studybot.cogs.study_plan",
            "studybot.cogs.wellness",
            "studybot.cogs.focus",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog読み込み完了: {cog}")
            except Exception as e:
                logger.error(f"Cog読み込み失敗 {cog}: {e}")

        # スラッシュコマンド同期
        await self.tree.sync()
        logger.info("スラッシュコマンド同期完了")

    async def on_ready(self) -> None:
        """Bot接続完了"""
        logger.info(f"Bot起動完了: {self.user} (ID: {self.user.id})")
        logger.info(f"接続サーバー数: {len(self.guilds)}")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📚 /pomodoro start で学習開始",
            )
        )

    async def close(self) -> None:
        """シャットダウン処理"""
        await self.db_manager.close()
        await super().close()


async def main() -> None:
    bot = StudyBot()
    try:
        await bot.start(settings.DISCORD_TOKEN)
    finally:
        await bot.close()


if __name__ == "__main__":
    if not settings.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN が設定されていません")
        sys.exit(1)

    asyncio.run(main())
