"""ゲーミフィケーションのテスト"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from studybot.config.constants import LEVEL_FORMULA, XP_REWARDS
from studybot.managers.gamification_manager import GamificationManager


@pytest.fixture
def gamification_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = GamificationManager(pool)
    return manager, conn


def test_level_formula():
    """レベル計算式テスト: level² × 100"""
    assert LEVEL_FORMULA(1) == 100
    assert LEVEL_FORMULA(2) == 400
    assert LEVEL_FORMULA(5) == 2500
    assert LEVEL_FORMULA(10) == 10000


def test_calculate_level():
    """累計XPからレベル計算"""
    manager = GamificationManager.__new__(GamificationManager)

    # 0 XP = Level 1
    assert manager._calculate_level(0) == 1

    # 400 XP = Level 2 (need 400 for level 2)
    assert manager._calculate_level(400) == 2

    # 399 XP = Level 1
    assert manager._calculate_level(399) == 1

    # 1300 XP = Level 3 (400 + 900 = 1300)
    assert manager._calculate_level(1300) == 3


@pytest.mark.asyncio
async def test_add_xp(gamification_manager):
    """XP付与テスト"""
    manager, conn = gamification_manager

    conn.execute.return_value = None  # xp_transaction insert
    conn.fetchrow.side_effect = [
        # get_challenge_xp_multiplier returns None (no active challenge)
        None,
        # add_xp returns updated user_levels row
        {
            "user_id": 123,
            "xp": 410,
            "level": 1,
            "streak_days": 0,
            "last_study_date": None,
            "updated_at": None,
        },
        # get_milestone returns None (no milestone at level 2)
        None,
    ]

    result = await manager.add_xp(123, 10, "テスト")
    assert result["xp_gained"] == 10
    assert result["total_xp"] == 410


@pytest.mark.asyncio
async def test_check_streak_new_day(gamification_manager):
    """連続学習チェック - 新しい日"""
    manager, conn = gamification_manager

    yesterday = date.today() - timedelta(days=1)
    conn.fetchrow.return_value = {
        "user_id": 123,
        "xp": 100,
        "level": 1,
        "streak_days": 3,
        "last_study_date": yesterday,
        "updated_at": None,
    }
    conn.execute.return_value = None

    result = await manager.check_streak(123)
    assert result["streak"] == 4
    assert result["bonus"] is False


@pytest.mark.asyncio
async def test_check_streak_reset(gamification_manager):
    """連続学習チェック - リセット"""
    manager, conn = gamification_manager

    two_days_ago = date.today() - timedelta(days=2)
    conn.fetchrow.return_value = {
        "user_id": 123,
        "xp": 100,
        "level": 1,
        "streak_days": 5,
        "last_study_date": two_days_ago,
        "updated_at": None,
    }
    conn.execute.return_value = None

    result = await manager.check_streak(123)
    assert result["streak"] == 1  # reset to 1


@pytest.mark.asyncio
async def test_check_streak_7day_bonus(gamification_manager):
    """7日連続ボーナス"""
    manager, conn = gamification_manager

    yesterday = date.today() - timedelta(days=1)
    conn.fetchrow.side_effect = [
        # get_user_level
        {
            "user_id": 123,
            "xp": 100,
            "level": 1,
            "streak_days": 6,
            "last_study_date": yesterday,
            "updated_at": None,
        },
        # add_xp (for streak bonus)
        {
            "user_id": 123,
            "xp": 150,
            "level": 1,
            "streak_days": 7,
            "last_study_date": None,
            "updated_at": None,
        },
    ]
    conn.execute.return_value = None

    result = await manager.check_streak(123)
    assert result["streak"] == 7
    assert result["bonus"] is True


def test_xp_rewards_defined():
    """XP報酬が定義されていること"""
    assert "pomodoro_complete" in XP_REWARDS
    assert "task_complete_high" in XP_REWARDS
    assert "study_log" in XP_REWARDS
    assert "streak_bonus" in XP_REWARDS
    assert XP_REWARDS["pomodoro_complete"] == 10
    assert XP_REWARDS["streak_bonus"] == 50


# --- Feature 1: Streak Details テスト ---


@pytest.mark.asyncio
async def test_get_streak_details(gamification_manager):
    """ストリーク詳細情報の取得"""
    manager, conn = gamification_manager

    conn.fetchrow.return_value = {
        "streak_days": 10,
        "last_study_date": date.today(),
        "best_streak": 15,
    }

    result = await manager.get_streak_details(123)
    assert result is not None
    assert result["streak_days"] == 10
    assert result["best_streak"] == 15
    assert result["next_milestone"] == 14
    assert result["days_until_milestone"] == 4


@pytest.mark.asyncio
async def test_get_streak_details_no_user(gamification_manager):
    """ストリーク詳細 - ユーザーが存在しない場合"""
    manager, conn = gamification_manager

    conn.fetchrow.return_value = None

    result = await manager.get_streak_details(999)
    assert result is None


@pytest.mark.asyncio
async def test_get_streak_details_milestone_7(gamification_manager):
    """ストリーク詳細 - 次のマイルストーンが7日"""
    manager, conn = gamification_manager

    conn.fetchrow.return_value = {
        "streak_days": 3,
        "last_study_date": date.today(),
        "best_streak": 5,
    }

    result = await manager.get_streak_details(123)
    assert result["next_milestone"] == 7
    assert result["days_until_milestone"] == 4


@pytest.mark.asyncio
async def test_get_streak_details_milestone_100(gamification_manager):
    """ストリーク詳細 - 次のマイルストーンが100日"""
    manager, conn = gamification_manager

    conn.fetchrow.return_value = {
        "streak_days": 65,
        "last_study_date": date.today(),
        "best_streak": 65,
    }

    result = await manager.get_streak_details(123)
    assert result["next_milestone"] == 100
    assert result["days_until_milestone"] == 35


@pytest.mark.asyncio
async def test_get_streak_details_all_milestones_achieved(gamification_manager):
    """ストリーク詳細 - 全マイルストーン達成済み"""
    manager, conn = gamification_manager

    conn.fetchrow.return_value = {
        "streak_days": 120,
        "last_study_date": date.today(),
        "best_streak": 120,
    }

    result = await manager.get_streak_details(123)
    assert result["next_milestone"] is None
    assert result["days_until_milestone"] == 0


# --- Feature 1: Repository テスト ---


@pytest.mark.asyncio
async def test_repo_get_streak_details(mock_db_pool):
    """リポジトリ: ストリーク詳細取得"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetchrow.return_value = {
        "streak_days": 5,
        "last_study_date": date.today(),
        "best_streak": 10,
    }

    result = await repo.get_streak_details(123)
    assert result["streak_days"] == 5
    assert result["best_streak"] == 10


@pytest.mark.asyncio
async def test_repo_get_streak_details_none(mock_db_pool):
    """リポジトリ: ストリーク詳細 - ユーザー不在"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetchrow.return_value = None

    result = await repo.get_streak_details(999)
    assert result is None


# --- Feature 2: Streak Reminder テスト ---


@pytest.mark.asyncio
async def test_repo_get_users_needing_streak_reminder(mock_db_pool):
    """リポジトリ: ストリークリマインダー対象ユーザー取得"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetch.return_value = [
        {"user_id": 111, "streak_days": 5},
        {"user_id": 222, "streak_days": 10},
    ]

    result = await repo.get_users_needing_streak_reminder(date.today())
    assert len(result) == 2
    assert result[0]["user_id"] == 111
    assert result[1]["streak_days"] == 10


@pytest.mark.asyncio
async def test_repo_get_users_needing_streak_reminder_empty(mock_db_pool):
    """リポジトリ: ストリークリマインダー対象なし"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetch.return_value = []

    result = await repo.get_users_needing_streak_reminder(date.today())
    assert result == []


@pytest.mark.asyncio
async def test_streak_protection_dm_sends_messages(mock_db_pool, mock_bot):
    """ストリーク保護DM: メッセージ送信テスト"""
    from studybot.cogs.gamification import GamificationCog

    pool, conn = mock_db_pool
    manager = GamificationManager(pool)

    conn.fetch.return_value = [
        {"user_id": 111, "streak_days": 5},
    ]

    mock_user = AsyncMock()
    mock_user.send = AsyncMock()
    mock_bot.get_user.return_value = mock_user

    cog = GamificationCog(mock_bot, manager)
    await cog.streak_protection_dm()

    mock_user.send.assert_called_once_with(
        "🔥 5日連続学習中！今日もあと少し学習して記録を守りましょう！"
    )


@pytest.mark.asyncio
async def test_streak_protection_dm_fetch_user(mock_db_pool, mock_bot):
    """ストリーク保護DM: get_user失敗時にfetch_userを使用"""
    from studybot.cogs.gamification import GamificationCog

    pool, conn = mock_db_pool
    manager = GamificationManager(pool)

    conn.fetch.return_value = [
        {"user_id": 222, "streak_days": 3},
    ]

    mock_user = AsyncMock()
    mock_user.send = AsyncMock()
    mock_bot.get_user.return_value = None
    mock_bot.fetch_user = AsyncMock(return_value=mock_user)

    cog = GamificationCog(mock_bot, manager)
    await cog.streak_protection_dm()

    mock_bot.fetch_user.assert_called_once_with(222)
    mock_user.send.assert_called_once()


@pytest.mark.asyncio
async def test_streak_protection_dm_forbidden(mock_db_pool, mock_bot):
    """ストリーク保護DM: DM送信拒否時にエラーにならない"""
    from studybot.cogs.gamification import GamificationCog

    pool, conn = mock_db_pool
    manager = GamificationManager(pool)

    conn.fetch.return_value = [
        {"user_id": 333, "streak_days": 7},
    ]

    mock_user = AsyncMock()
    mock_user.send = AsyncMock(
        side_effect=discord.Forbidden(MagicMock(), "Cannot send messages")
    )
    mock_bot.get_user.return_value = mock_user

    cog = GamificationCog(mock_bot, manager)
    # Should not raise
    await cog.streak_protection_dm()


@pytest.mark.asyncio
async def test_streak_protection_dm_no_users(mock_db_pool, mock_bot):
    """ストリーク保護DM: 対象ユーザーなし"""
    from studybot.cogs.gamification import GamificationCog

    pool, conn = mock_db_pool
    manager = GamificationManager(pool)

    conn.fetch.return_value = []

    cog = GamificationCog(mock_bot, manager)
    await cog.streak_protection_dm()

    mock_bot.get_user.assert_not_called()


# --- Feature 3: Daily Leaderboard テスト ---


@pytest.mark.asyncio
async def test_repo_get_daily_top_earners(mock_db_pool):
    """リポジトリ: デイリートップ取得"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetch.return_value = [
        {"user_id": 1, "username": "Alice", "daily_xp": 500},
        {"user_id": 2, "username": "Bob", "daily_xp": 300},
    ]

    result = await repo.get_daily_top_earners(limit=5)
    assert len(result) == 2
    assert result[0]["daily_xp"] == 500
    assert result[1]["username"] == "Bob"


@pytest.mark.asyncio
async def test_repo_get_daily_top_earners_empty(mock_db_pool):
    """リポジトリ: デイリートップ - データなし"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetch.return_value = []

    result = await repo.get_daily_top_earners(limit=5)
    assert result == []


@pytest.mark.asyncio
async def test_daily_leaderboard_post_sends_embed(mock_db_pool, mock_bot):
    """デイリーリーダーボード: 投稿テスト"""
    from studybot.cogs.leaderboard import LeaderboardCog

    pool, conn = mock_db_pool

    conn.fetch.return_value = [
        {"user_id": 1, "username": "Alice", "daily_xp": 500},
        {"user_id": 2, "username": "Bob", "daily_xp": 300},
    ]

    mock_channel = AsyncMock()
    mock_channel.name = "leaderboard"

    mock_guild = MagicMock()
    mock_guild.id = 999
    mock_guild.text_channels = [mock_channel]
    mock_bot.guilds = [mock_guild]

    cog = LeaderboardCog(mock_bot, pool)
    await cog.daily_leaderboard_post()

    mock_channel.send.assert_called_once()
    call_kwargs = mock_channel.send.call_args
    embed = call_kwargs.kwargs.get("embed") or call_kwargs[1].get("embed")
    assert embed is not None
    assert "Alice" in embed.description
    assert "Bob" in embed.description


@pytest.mark.asyncio
async def test_daily_leaderboard_post_no_data(mock_db_pool, mock_bot):
    """デイリーリーダーボード: データなしで投稿しない"""
    from studybot.cogs.leaderboard import LeaderboardCog

    pool, conn = mock_db_pool

    conn.fetch.return_value = []

    mock_guild = MagicMock()
    mock_guild.text_channels = []
    mock_bot.guilds = [mock_guild]

    cog = LeaderboardCog(mock_bot, pool)
    await cog.daily_leaderboard_post()

    # No channels should have been messaged
    for ch in mock_guild.text_channels:
        ch.send.assert_not_called()


@pytest.mark.asyncio
async def test_daily_leaderboard_post_study_log_channel(mock_db_pool, mock_bot):
    """デイリーリーダーボード: study-logチャンネルへのフォールバック"""
    from studybot.cogs.leaderboard import LeaderboardCog

    pool, conn = mock_db_pool

    conn.fetch.return_value = [
        {"user_id": 1, "username": "Charlie", "daily_xp": 100},
    ]

    mock_channel = AsyncMock()
    mock_channel.name = "study-log"

    other_channel = AsyncMock()
    other_channel.name = "general"

    mock_guild = MagicMock()
    mock_guild.id = 888
    mock_guild.text_channels = [other_channel, mock_channel]
    mock_bot.guilds = [mock_guild]

    cog = LeaderboardCog(mock_bot, pool)
    await cog.daily_leaderboard_post()

    mock_channel.send.assert_called_once()
    other_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_find_leaderboard_channel_priority(mock_db_pool, mock_bot):
    """チャンネル検索: leaderboardチャンネルが優先"""
    from studybot.cogs.leaderboard import LeaderboardCog

    pool, conn = mock_db_pool

    lb_channel = MagicMock()
    lb_channel.name = "leaderboard"

    sl_channel = MagicMock()
    sl_channel.name = "study-log"

    mock_guild = MagicMock()
    mock_guild.text_channels = [sl_channel, lb_channel]

    cog = LeaderboardCog(mock_bot, pool)
    result = cog._find_leaderboard_channel(mock_guild)
    assert result == lb_channel


@pytest.mark.asyncio
async def test_find_leaderboard_channel_none(mock_db_pool, mock_bot):
    """チャンネル検索: 該当チャンネルなし"""
    from studybot.cogs.leaderboard import LeaderboardCog

    pool, conn = mock_db_pool

    other_channel = MagicMock()
    other_channel.name = "general"

    mock_guild = MagicMock()
    mock_guild.text_channels = [other_channel]

    cog = LeaderboardCog(mock_bot, pool)
    result = cog._find_leaderboard_channel(mock_guild)
    assert result is None
