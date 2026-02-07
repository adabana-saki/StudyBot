"""テスト共通フィクスチャ"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class MockAsyncContextManager:
    """async with をサポートするモック"""

    def __init__(self, return_value):
        self._return_value = return_value

    async def __aenter__(self):
        return self._return_value

    async def __aexit__(self, *args):
        return False


@pytest.fixture
def mock_db_pool():
    """モックDB接続プール"""
    pool = MagicMock()
    conn = AsyncMock()

    # pool.acquire() がasync context managerを返す
    pool.acquire.return_value = MockAsyncContextManager(conn)

    # conn.transaction() がasync context managerを返す
    conn.transaction = MagicMock(return_value=MockAsyncContextManager(conn))

    return pool, conn


@pytest.fixture
def mock_bot():
    """モックDiscord Bot"""
    bot = MagicMock()
    bot.get_cog = MagicMock(return_value=None)
    bot.get_channel = MagicMock(return_value=None)
    bot.get_user = MagicMock(return_value=None)
    bot.guilds = []
    bot.wait_until_ready = AsyncMock()
    return bot


@pytest.fixture
def mock_interaction():
    """モックDiscord Interaction"""
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 123456789
    interaction.user.display_name = "TestUser"
    interaction.user.display_avatar = MagicMock()
    interaction.user.display_avatar.url = "https://example.com/avatar.png"
    interaction.guild_id = 987654321
    interaction.channel_id = 111222333
    interaction.channel = AsyncMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction
