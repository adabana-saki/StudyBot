"""StudyBot - AI搭載学習支援Discord Bot"""

import asyncio
import logging
import sys

import discord
from discord.ext import commands

from studybot.config.settings import settings
from studybot.database.manager import DatabaseManager
from studybot.services.event_publisher import EventPublisher
from studybot.services.openai_service import set_redis_client
from studybot.services.redis_client import RedisClient
from studybot.services.session_sync import SessionSyncService

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
        intents.voice_states = True

        super().__init__(command_prefix="!", intents=intents)
        self.db_manager = DatabaseManager()
        self.redis_client: RedisClient | None = None
        self.event_publisher: EventPublisher | None = None
        self.session_sync: SessionSyncService | None = None

    async def setup_hook(self) -> None:
        """Bot接続前の初期化"""
        # データベース初期化
        if not await self.db_manager.initialize():
            logger.error("データベース初期化に失敗しました")
            return

        self.db_pool = self.db_manager.pool

        # Redis初期化
        if settings.REDIS_URL:
            try:
                self.redis_client = RedisClient(settings.REDIS_URL)
                await self.redis_client.connect()
                self.event_publisher = EventPublisher(self.redis_client, db_pool=self.db_pool)
                self.session_sync = SessionSyncService(self.db_pool, self.redis_client)
                set_redis_client(self.redis_client)
                logger.info("Redis + SessionSync + AIキャッシュ接続完了")
            except Exception as e:
                logger.warning(f"Redis接続失敗（イベント機能無効）: {e}")
                self.redis_client = None
                self.event_publisher = None

        # Cog読み込み（critical=True のCogが失敗した場合は起動中止）
        cog_list = [
            # Core（必須）
            ("studybot.cogs.pomodoro", True),
            ("studybot.cogs.study_log", True),
            ("studybot.cogs.todo", True),
            ("studybot.cogs.gamification", True),
            ("studybot.cogs.leaderboard", False),
            ("studybot.cogs.ai_doc", False),
            ("studybot.cogs.phone_nudge", False),
            # Phase 2
            ("studybot.cogs.shop", False),
            ("studybot.cogs.raid", False),
            ("studybot.cogs.achievement", False),
            ("studybot.cogs.flashcard", False),
            ("studybot.cogs.study_plan", False),
            ("studybot.cogs.wellness", False),
            ("studybot.cogs.focus", False),
            # Phase 3
            ("studybot.cogs.voice_study", False),
            ("studybot.cogs.help", False),
            ("studybot.cogs.admin", False),
            # Phase 5
            ("studybot.cogs.buddy", False),
            ("studybot.cogs.challenge", False),
            ("studybot.cogs.insights", False),
            # Phase 6
            ("studybot.cogs.quest", False),
            ("studybot.cogs.team", False),
            ("studybot.cogs.learning_path", False),
            # Phase 8
            ("studybot.cogs.social_notify", False),
            ("studybot.cogs.battle", False),
            ("studybot.cogs.scheduled_actions", False),
            ("studybot.cogs.study_room", False),
            # Phase 9
            ("studybot.cogs.market", False),
        ]

        for cog, critical in cog_list:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog読み込み完了: {cog}")
            except Exception as e:
                if critical:
                    logger.critical(f"必須Cog読み込み失敗 {cog}: {e}")
                    sys.exit(1)
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
        if self.redis_client:
            await self.redis_client.close()
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
