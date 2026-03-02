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

    mock_user.send.assert_called_once()
    call_kwargs = mock_user.send.call_args
    assert "embed" in call_kwargs.kwargs
    embed = call_kwargs.kwargs["embed"]
    assert "5日" in embed.description
    assert "連続学習" in embed.description


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
    mock_user.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Cannot send messages"))
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


# =============================================================
# Phase 1: 離脱検知・フォーカススコア・自己ベスト・ウェルカムガイド
# =============================================================


# --- 機能1: 離脱検知DM テスト ---


@pytest.mark.asyncio
async def test_get_churned_users(mock_db_pool):
    """リポジトリ: 離脱ユーザー取得"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetch.return_value = [
        {
            "user_id": 111,
            "streak_days": 0,
            "best_streak": 15,
            "last_study_date": date.today() - timedelta(days=5),
        },
    ]

    result = await repo.get_churned_users(min_streak=10, inactive_days=2)
    assert len(result) == 1
    assert result[0]["best_streak"] == 15


@pytest.mark.asyncio
async def test_churn_detection_dm_sends(mock_db_pool, mock_bot):
    """離脱検知DM: メッセージ送信テスト"""
    from studybot.cogs.gamification import GamificationCog

    pool, conn = mock_db_pool
    manager = GamificationManager(pool)

    # get_churned_users
    conn.fetch.return_value = [
        {
            "user_id": 111,
            "streak_days": 0,
            "best_streak": 20,
            "last_study_date": date.today() - timedelta(days=3),
        },
    ]

    # has_recent_churn_dm returns 0 (not sent)
    conn.fetchval.return_value = 0
    conn.execute.return_value = None

    mock_user = AsyncMock()
    mock_user.send = AsyncMock()
    mock_bot.get_user.return_value = mock_user

    cog = GamificationCog(mock_bot, manager)
    await cog.churn_detection_dm()

    mock_user.send.assert_called_once()
    call_kwargs = mock_user.send.call_args
    embed = call_kwargs.kwargs["embed"]
    assert "20日" in embed.description
    assert "お久しぶり" in embed.title


@pytest.mark.asyncio
async def test_churn_dm_not_resent_within_7_days(mock_db_pool, mock_bot):
    """離脱検知DM: 7日以内に再送しない"""
    from studybot.cogs.gamification import GamificationCog

    pool, conn = mock_db_pool
    manager = GamificationManager(pool)

    conn.fetch.return_value = [
        {
            "user_id": 111,
            "streak_days": 0,
            "best_streak": 15,
            "last_study_date": date.today() - timedelta(days=5),
        },
    ]

    # has_recent_churn_dm returns 1 (already sent)
    conn.fetchval.return_value = 1

    mock_user = AsyncMock()
    mock_bot.get_user.return_value = mock_user

    cog = GamificationCog(mock_bot, manager)
    await cog.churn_detection_dm()

    mock_user.send.assert_not_called()


# --- 機能2: フォーカススコア テスト ---


@pytest.mark.asyncio
async def test_calculate_focus_score_no_data(gamification_manager):
    """フォーカススコア: データなし → スコア0"""
    manager, conn = gamification_manager

    # All sub-queries return 0
    conn.fetchrow.side_effect = [
        {"total": 0, "completed": 0},  # pomodoro
        {"total": 0, "completed": 0},  # focus
        {"completed": 0, "total": 0},  # lock
        {"study_days": 0},  # consistency
        {"breach_count": 0},  # app breach
    ]
    conn.fetchval.return_value = 0  # monitored_sessions

    result = await manager.calculate_focus_score(123)
    # app_discipline=1.0 → *15=15 (他は全て0)
    assert result["score"] == 15
    assert result["grade"] == "D"
    assert result["components"]["completion_rate"] == 0
    assert result["components"]["lock_success"] == 0


@pytest.mark.asyncio
async def test_calculate_focus_score_full_data(gamification_manager):
    """フォーカススコア: フルデータ"""
    manager, conn = gamification_manager

    conn.fetchrow.side_effect = [
        {"total": 10, "completed": 8},  # pomodoro: 80%
        {"total": 5, "completed": 4},  # focus: 80% → combined 12/15 = 80%
        {"completed": 7, "total": 10},  # lock: 70%
        {"study_days": 10},  # consistency: 10/14 = ~71%
        {"breach_count": 0},  # app breach
    ]
    conn.fetchval.return_value = 0  # monitored_sessions

    result = await manager.calculate_focus_score(123)
    # completion_rate = 12/15 = 0.8 → *30 = 24
    # lock_success = 7/10 = 0.7 → *20 = 14
    # consistency = 10/14 ≈ 0.714 → *20 = 14.28
    # session_quality = 0.8 → *15 = 12
    # app_discipline = 1.0 → *15 = 15
    # total ≈ 79
    assert result["score"] == 79
    assert result["grade"] == "A"


@pytest.mark.asyncio
async def test_focus_score_grade(gamification_manager):
    """フォーカススコア: グレード判定"""
    manager, conn = gamification_manager

    # Perfect scores
    conn.fetchrow.side_effect = [
        {"total": 10, "completed": 10},  # pomo: 100%
        {"total": 0, "completed": 0},  # focus
        {"completed": 10, "total": 10},  # lock: 100%
        {"study_days": 14},  # consistency: 100%
        {"breach_count": 0},  # app breach
    ]
    conn.fetchval.return_value = 0  # monitored_sessions

    result = await manager.calculate_focus_score(123)
    # completion=1.0→30, lock=1.0→20, consistency=1.0→20, quality=1.0→15, app=1.0→15
    assert result["score"] == 100
    assert result["grade"] == "S"


# --- 機能3: 自己ベスト テスト ---


@pytest.mark.asyncio
async def test_update_personal_bests_new_record(mock_db_pool):
    """リポジトリ: 自己ベスト更新"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    # All updates succeed
    conn.execute.return_value = "UPDATE 1"

    result = await repo.update_personal_bests(123, streak=10, daily_minutes=120, weekly_minutes=500)
    assert "best_streak" in result
    assert result["best_streak"] == 10
    assert "best_daily_minutes" in result
    assert "best_weekly_minutes" in result


@pytest.mark.asyncio
async def test_update_personal_bests_no_change(mock_db_pool):
    """リポジトリ: 自己ベスト更新なし"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    # No rows updated
    conn.execute.return_value = "UPDATE 0"

    result = await repo.update_personal_bests(123, streak=5, daily_minutes=30)
    assert result == {}


@pytest.mark.asyncio
async def test_check_personal_bests_after_study(gamification_manager):
    """マネージャー: 学習後の自己ベストチェック"""
    manager, conn = gamification_manager

    # get_user_level
    conn.fetchrow.return_value = {
        "user_id": 123,
        "xp": 500,
        "level": 2,
        "streak_days": 5,
        "last_study_date": date.today(),
        "updated_at": None,
    }

    # get_today_study_minutes, get_week_study_minutes
    conn.fetchval.side_effect = [120, 500]

    # update_personal_bests: streak update succeeds, daily/weekly don't
    conn.execute.side_effect = ["UPDATE 1", "UPDATE 0", "UPDATE 0"]

    result = await manager.check_personal_bests(123)
    assert "best_streak" in result
    assert result["best_streak"] == 5


@pytest.mark.asyncio
async def test_get_personal_bests(mock_db_pool):
    """リポジトリ: 自己ベスト取得"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetchrow.return_value = {
        "best_streak": 15,
        "best_daily_minutes": 180,
        "best_weekly_minutes": 800,
    }

    result = await repo.get_personal_bests(123)
    assert result["best_streak"] == 15
    assert result["best_daily_minutes"] == 180
    assert result["best_weekly_minutes"] == 800


@pytest.mark.asyncio
async def test_get_personal_bests_no_user(mock_db_pool):
    """リポジトリ: 自己ベスト取得 - ユーザー不在"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    conn.fetchrow.return_value = None

    result = await repo.get_personal_bests(999)
    assert result == {"best_streak": 0, "best_daily_minutes": 0, "best_weekly_minutes": 0}


# --- 機能4: ウェルカムガイド テスト ---


@pytest.mark.asyncio
async def test_ensure_user_returns_is_new(gamification_manager):
    """マネージャー: ensure_userが新規フラグを返す"""
    manager, conn = gamification_manager

    conn.execute.return_value = None  # ensure_user (base)
    conn.fetchrow.return_value = {
        "user_id": 123,
        "xp": 0,
        "level": 1,
        "streak_days": 0,
        "last_study_date": None,
        "updated_at": None,
    }

    level_data, is_new = await manager.ensure_user(123, "TestUser")
    assert level_data["user_id"] == 123
    assert isinstance(is_new, bool)


@pytest.mark.asyncio
async def test_ensure_user_level_with_flag_new(mock_db_pool):
    """リポジトリ: 新規ユーザー判定"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    # INSERT RETURNING returns row (new user)
    conn.fetchrow.return_value = {
        "user_id": 123,
        "xp": 0,
        "level": 1,
        "streak_days": 0,
        "last_study_date": None,
        "updated_at": None,
    }

    result, is_new = await repo.ensure_user_level_with_flag(123)
    assert is_new is True
    assert result["user_id"] == 123


@pytest.mark.asyncio
async def test_ensure_user_level_with_flag_existing(mock_db_pool):
    """リポジトリ: 既存ユーザー判定"""
    from studybot.repositories.gamification_repository import GamificationRepository

    pool, conn = mock_db_pool
    repo = GamificationRepository(pool)

    # INSERT RETURNING returns None (conflict), then SELECT returns row
    conn.fetchrow.side_effect = [
        None,
        {
            "user_id": 123,
            "xp": 500,
            "level": 3,
            "streak_days": 10,
            "last_study_date": date.today(),
            "updated_at": None,
        },
    ]

    result, is_new = await repo.ensure_user_level_with_flag(123)
    assert is_new is False
    assert result["xp"] == 500


@pytest.mark.asyncio
async def test_welcome_guide_sent_to_new_user(mock_db_pool, mock_bot):
    """ウェルカムガイド: 新規ユーザーにDM送信"""
    from studybot.cogs.gamification import GamificationCog

    pool, conn = mock_db_pool
    manager = GamificationManager(pool)

    # ensure_user (base)
    conn.execute.return_value = None
    # ensure_user_level_with_flag: INSERT returns row (new user)
    conn.fetchrow.return_value = {
        "user_id": 123,
        "xp": 0,
        "level": 1,
        "streak_days": 0,
        "last_study_date": None,
        "updated_at": None,
    }

    mock_user = AsyncMock()
    mock_user.id = 123
    mock_user.display_name = "TestUser"
    mock_user.send = AsyncMock()

    mock_interaction = AsyncMock()
    mock_interaction.user = mock_user

    cog = GamificationCog(mock_bot, manager)
    await cog._ensure_user_and_welcome(mock_interaction, 123, "TestUser")

    mock_user.send.assert_called_once()
    call_kwargs = mock_user.send.call_args
    embed = call_kwargs.kwargs["embed"]
    assert "ようこそ" in embed.title


@pytest.mark.asyncio
async def test_welcome_not_sent_to_existing_user(mock_db_pool, mock_bot):
    """ウェルカムガイド: 既存ユーザーにはDM送信しない"""
    from studybot.cogs.gamification import GamificationCog

    pool, conn = mock_db_pool
    manager = GamificationManager(pool)

    conn.execute.return_value = None
    # ensure_user_level_with_flag: INSERT returns None (conflict), then SELECT
    conn.fetchrow.side_effect = [
        None,
        {
            "user_id": 123,
            "xp": 500,
            "level": 3,
            "streak_days": 10,
            "last_study_date": date.today(),
            "updated_at": None,
        },
    ]

    mock_user = AsyncMock()
    mock_user.id = 123
    mock_user.display_name = "TestUser"
    mock_user.send = AsyncMock()

    mock_interaction = AsyncMock()
    mock_interaction.user = mock_user

    cog = GamificationCog(mock_bot, manager)
    await cog._ensure_user_and_welcome(mock_interaction, 123, "TestUser")

    mock_user.send.assert_not_called()


# --- 離脱検知: NudgeRepository テスト ---


@pytest.mark.asyncio
async def test_nudge_repo_has_recent_churn_dm(mock_db_pool):
    """NudgeRepository: 離脱検知DM送信済み確認"""
    from studybot.repositories.nudge_repository import NudgeRepository

    pool, conn = mock_db_pool
    repo = NudgeRepository(pool)

    conn.fetchval.return_value = 1  # sent within 7 days

    result = await repo.has_recent_churn_dm(123, days=7)
    assert result is True


@pytest.mark.asyncio
async def test_nudge_repo_has_no_recent_churn_dm(mock_db_pool):
    """NudgeRepository: 離脱検知DM未送信"""
    from studybot.repositories.nudge_repository import NudgeRepository

    pool, conn = mock_db_pool
    repo = NudgeRepository(pool)

    conn.fetchval.return_value = 0

    result = await repo.has_recent_churn_dm(123, days=7)
    assert result is False


@pytest.mark.asyncio
async def test_nudge_repo_record_churn_dm(mock_db_pool):
    """NudgeRepository: 離脱検知DM記録"""
    from studybot.repositories.nudge_repository import NudgeRepository

    pool, conn = mock_db_pool
    repo = NudgeRepository(pool)

    conn.execute.return_value = None

    await repo.record_churn_dm(123)
    conn.execute.assert_called_once()


# =============================================================
# Phase 2: チームクエスト・バディ連携・スマートクエスト
# =============================================================


# --- チームクエスト テスト ---


@pytest.mark.asyncio
async def test_team_quest_generation(mock_db_pool):
    """TeamManager: チームクエスト生成"""
    from studybot.managers.team_manager import TeamManager

    pool, conn = mock_db_pool
    manager = TeamManager(pool)

    # get_team_quests returns empty (triggers generation)
    conn.fetch.return_value = []
    # create_team_quest returns ID
    conn.fetchval.return_value = 1

    quests = await manager.get_team_quests(team_id=1)
    assert len(quests) == 2  # 2 quests generated
    assert all(q["team_id"] == 1 for q in quests)
    assert all(q["progress"] == 0 for q in quests)


@pytest.mark.asyncio
async def test_team_quest_progress_update(mock_db_pool):
    """TeamManager: チームクエスト進捗更新"""
    from studybot.managers.team_manager import TeamManager

    pool, conn = mock_db_pool
    manager = TeamManager(pool)

    # get_user_team_ids
    conn.fetch.side_effect = [
        [{"team_id": 1}, {"team_id": 2}],  # user is in 2 teams
        [],  # update returns for team 1
        [],  # update returns for team 2
    ]
    conn.execute.return_value = None

    await manager.update_team_quest_progress(user_id=123, quest_type="team_pomodoro", delta=1)
    # Should have updated both teams
    assert conn.execute.call_count >= 2 or conn.fetch.call_count >= 1


@pytest.mark.asyncio
async def test_team_quest_claim_success(mock_db_pool):
    """TeamManager: チームクエスト報酬受取成功"""
    from studybot.managers.team_manager import TeamManager

    pool, conn = mock_db_pool
    manager = TeamManager(pool)

    # get_team_quest_by_id
    conn.fetchrow.side_effect = [
        {
            "id": 1,
            "team_id": 1,
            "quest_type": "team_pomodoro",
            "target": 5,
            "progress": 5,
            "completed": True,
            "claimed": False,
            "reward_xp": 50,
            "reward_coins": 40,
        },
        # claim_team_quest returns updated row
        {
            "id": 1,
            "team_id": 1,
            "quest_type": "team_pomodoro",
            "reward_xp": 50,
            "reward_coins": 40,
        },
    ]

    result = await manager.claim_team_quest(team_id=1, quest_id=1)
    assert "error" not in result
    assert result["reward_xp"] == 50
    assert result["reward_coins"] == 40


@pytest.mark.asyncio
async def test_team_quest_claim_not_completed(mock_db_pool):
    """TeamManager: 未完了クエスト報酬受取失敗"""
    from studybot.managers.team_manager import TeamManager

    pool, conn = mock_db_pool
    manager = TeamManager(pool)

    conn.fetchrow.return_value = {
        "id": 1,
        "team_id": 1,
        "quest_type": "team_pomodoro",
        "completed": False,
        "claimed": False,
    }

    result = await manager.claim_team_quest(team_id=1, quest_id=1)
    assert "error" in result
    assert "完了していません" in result["error"]


@pytest.mark.asyncio
async def test_team_quest_label():
    """TeamManager: クエストラベル取得"""
    from studybot.managers.team_manager import TeamManager

    manager = TeamManager.__new__(TeamManager)

    assert manager.get_team_quest_label("team_pomodoro") == "チーム合計ポモドーロ"
    assert manager.get_team_quest_label("team_study_minutes") == "チーム合計学習時間"
    assert manager.get_team_quest_label("unknown") == "unknown"


# --- バディセッション連携 テスト ---


@pytest.mark.asyncio
async def test_buddy_concurrent_session_detected(mock_db_pool):
    """BuddyManager: 同時セッション検出"""
    from studybot.managers.buddy_manager import BuddyManager

    pool, conn = mock_db_pool
    manager = BuddyManager(pool)

    # get active matches
    conn.fetch.return_value = [
        {"user_a": 123, "user_b": 456},
    ]
    # buddy has active pomodoro session
    conn.fetchrow.return_value = {"1": 1}

    result = await manager.check_concurrent_session(123)
    assert result is True


@pytest.mark.asyncio
async def test_buddy_no_concurrent_session(mock_db_pool):
    """BuddyManager: 同時セッションなし"""
    from studybot.managers.buddy_manager import BuddyManager

    pool, conn = mock_db_pool
    manager = BuddyManager(pool)

    # no active matches
    conn.fetch.return_value = []

    result = await manager.check_concurrent_session(123)
    assert result is False


# --- スマートクエスト テスト ---


def test_generate_smart_quests():
    """スマートクエスト生成"""
    from studybot.managers.quest_manager import _generate_smart_quests

    activity = {
        "pomodoro_count": 10,
        "study_minutes": 300,
        "tasks_completed": 5,
        "log_count": 8,
    }

    quests = _generate_smart_quests(user_id=123, quest_date=date.today(), activity=activity)
    assert len(quests) == 3
    assert all(q["user_id"] == 123 for q in quests)
    assert all(q["reward_xp"] > 0 for q in quests)


def test_generate_smart_quests_no_activity():
    """スマートクエスト: アクティビティなし → ランダムフォールバック"""
    from studybot.managers.quest_manager import _generate_smart_quests

    quests = _generate_smart_quests(user_id=123, quest_date=date.today(), activity=None)
    assert len(quests) == 3


def test_generate_chain_bonus_quest():
    """チェインボーナスクエスト生成"""
    from studybot.managers.quest_manager import _generate_chain_bonus_quest

    bonus = _generate_chain_bonus_quest(user_id=123, quest_date=date.today(), chain_days=7)
    assert bonus is not None
    assert bonus["reward_xp"] > 0
    assert bonus["reward_coins"] > 0
    assert bonus["target"] > 0


# =============================================================
# Phase 3: 学習タイミング・週次イベント・シーズンパス・ウェルネス推奨
# =============================================================


# --- 学習タイミング分析 テスト ---


@pytest.mark.asyncio
async def test_optimal_timing_analysis(gamification_manager):
    """GamificationManager: 学習タイミング分析"""
    manager, conn = gamification_manager

    # hourly data
    conn.fetch.side_effect = [
        [
            {"hour": 9, "total_minutes": 300, "session_count": 10},
            {"hour": 14, "total_minutes": 200, "session_count": 8},
            {"hour": 20, "total_minutes": 150, "session_count": 5},
        ],
        # daily data
        [
            {"dow": 1, "total_minutes": 400, "session_count": 15},
            {"dow": 3, "total_minutes": 300, "session_count": 10},
        ],
    ]
    # avg pomo data
    conn.fetchrow.return_value = {
        "avg_work_minutes": 27.5,
        "total_completed": 20,
    }

    result = await manager.get_optimal_timing(123)
    assert result["has_data"] is True
    assert len(result["best_hours"]) == 3
    assert result["best_hours"][0]["hour"] == 9  # highest minutes
    assert result["recommended_pomo_minutes"] == 30  # 27.5 rounded to 30
    assert result["total_completed_pomos"] == 20


@pytest.mark.asyncio
async def test_optimal_timing_no_data(gamification_manager):
    """GamificationManager: タイミング分析データなし"""
    manager, conn = gamification_manager

    conn.fetch.side_effect = [[], []]
    conn.fetchrow.return_value = {
        "avg_work_minutes": None,
        "total_completed": 0,
    }

    result = await manager.get_optimal_timing(123)
    assert result["has_data"] is False
    assert result["recommended_pomo_minutes"] == 25  # default


# --- 週次イベント自動生成 テスト ---


@pytest.mark.asyncio
async def test_auto_generate_weekly_event(mock_db_pool):
    """ChallengeManager: 週次イベント自動生成"""
    from studybot.managers.challenge_manager import ChallengeManager

    pool, conn = mock_db_pool
    manager = ChallengeManager(pool)

    # list_challenges returns empty (no active challenges)
    conn.fetch.return_value = []
    # create_challenge returns ID
    conn.fetchval.return_value = 1
    conn.execute.return_value = None

    result = await manager.auto_generate_weekly_event(guild_id=999, creator_id=100)
    assert result is not None
    assert "challenge_id" in result
    assert result["challenge_id"] == 1


@pytest.mark.asyncio
async def test_auto_generate_weekly_event_skips_if_active(mock_db_pool):
    """ChallengeManager: アクティブイベント存在時にスキップ"""
    from studybot.managers.challenge_manager import ChallengeManager

    pool, conn = mock_db_pool
    manager = ChallengeManager(pool)

    # list_challenges returns existing active challenge
    conn.fetch.return_value = [{"id": 1, "name": "既存"}]

    result = await manager.auto_generate_weekly_event(guild_id=999, creator_id=100)
    assert result is None


# --- シーズンパス テスト ---


@pytest.mark.asyncio
async def test_season_progress_no_active_season(gamification_manager):
    """GamificationManager: アクティブシーズンなし"""
    manager, conn = gamification_manager

    conn.fetchrow.return_value = None  # no active season

    result = await manager.get_season_progress(123)
    assert result is None


@pytest.mark.asyncio
async def test_season_progress_with_data(gamification_manager):
    """GamificationManager: シーズン進捗取得"""
    manager, conn = gamification_manager

    conn.fetchrow.side_effect = [
        # get_active_season
        {
            "id": 1,
            "name": "シーズン1",
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=30),
            "status": "active",
        },
        # get_season_progress
        {"user_id": 123, "season_id": 1, "total_xp": 500, "tier": 3, "last_claimed_tier": 3},
    ]

    result = await manager.get_season_progress(123)
    assert result is not None
    assert result["total_xp"] == 500
    assert result["tier"] == 3
    assert result["next_tier"] is not None
    assert result["next_tier"]["tier"] == 4


@pytest.mark.asyncio
async def test_add_season_xp_tier_up(gamification_manager):
    """GamificationManager: シーズンXP追加でティアアップ"""
    manager, conn = gamification_manager

    conn.fetchrow.side_effect = [
        # get_active_season
        {
            "id": 1,
            "name": "シーズン1",
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=30),
            "status": "active",
        },
        # upsert_season_progress
        {"user_id": 123, "season_id": 1, "total_xp": 350, "tier": 1, "last_claimed_tier": 1},
    ]
    conn.execute.return_value = None  # update_season_tier

    result = await manager.add_season_xp(123, 250)
    assert result is not None
    assert result["total_xp"] == 350
    assert result["new_tier"] == 2  # 300 XP = tier 2
    assert len(result["tier_ups"]) == 1
    assert result["tier_ups"][0]["label"] == "ブロンズ II"


@pytest.mark.asyncio
async def test_add_season_xp_no_tier_change(gamification_manager):
    """GamificationManager: シーズンXP追加でティア変更なし"""
    manager, conn = gamification_manager

    conn.fetchrow.side_effect = [
        # get_active_season
        {
            "id": 1,
            "name": "シーズン1",
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=30),
            "status": "active",
        },
        # upsert_season_progress
        {"user_id": 123, "season_id": 1, "total_xp": 150, "tier": 1, "last_claimed_tier": 1},
    ]

    result = await manager.add_season_xp(123, 50)
    assert result is not None
    assert result["old_tier"] == 1
    assert result["new_tier"] == 1
    assert len(result["tier_ups"]) == 0


@pytest.mark.asyncio
async def test_season_leaderboard(gamification_manager):
    """GamificationManager: シーズンランキング"""
    manager, conn = gamification_manager

    conn.fetchrow.return_value = {
        "id": 1,
        "name": "シーズン1",
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=30),
        "status": "active",
    }
    conn.fetch.return_value = [
        {"user_id": 1, "username": "Alice", "total_xp": 5000, "tier": 8},
        {"user_id": 2, "username": "Bob", "total_xp": 3000, "tier": 7},
    ]

    result = await manager.get_season_leaderboard(10)
    assert len(result) == 2
    assert result[0]["username"] == "Alice"


# --- ウェルネス連携推奨 テスト ---


@pytest.mark.asyncio
async def test_wellness_recommendation_high_energy(mock_db_pool):
    """WellnessManager: 高エネルギー時の推奨"""
    from studybot.managers.wellness_manager import WellnessManager

    pool, conn = mock_db_pool
    manager = WellnessManager(pool)

    # get_today_log, then get_averages
    conn.fetchrow.side_effect = [
        {"mood": 4, "energy": 5, "stress": 1},
        {"avg_mood": 4.0, "avg_energy": 5.0, "avg_stress": 1.0, "log_count": 3},
    ]

    result = await manager.get_recommendation(123)
    assert result["has_data"] is True
    assert result["recommended_minutes"] == 50
    assert result["session_type"] == "deep_focus"


@pytest.mark.asyncio
async def test_wellness_recommendation_low_energy(mock_db_pool):
    """WellnessManager: 低エネルギー時の推奨"""
    from studybot.managers.wellness_manager import WellnessManager

    pool, conn = mock_db_pool
    manager = WellnessManager(pool)

    conn.fetchrow.side_effect = [
        {"mood": 2, "energy": 1, "stress": 4},
        {"avg_mood": 2.0, "avg_energy": 1.0, "avg_stress": 4.0, "log_count": 3},
    ]

    result = await manager.get_recommendation(123)
    assert result["has_data"] is True
    assert result["recommended_minutes"] == 15
    assert result["session_type"] == "light"
    assert len(result["extra_tips"]) >= 2  # mood <= 2 and energy <= 2


@pytest.mark.asyncio
async def test_wellness_recommendation_no_data(mock_db_pool):
    """WellnessManager: データなし"""
    from studybot.managers.wellness_manager import WellnessManager

    pool, conn = mock_db_pool
    manager = WellnessManager(pool)

    # get_today_log returns None
    conn.fetchrow.side_effect = [
        None,
        None,  # get_averages returns None
    ]

    result = await manager.get_recommendation(123)
    assert result["has_data"] is False


@pytest.mark.asyncio
async def test_wellness_recommendation_average_fallback(mock_db_pool):
    """WellnessManager: 今日のデータなし→平均値にフォールバック"""
    from studybot.managers.wellness_manager import WellnessManager

    pool, conn = mock_db_pool
    manager = WellnessManager(pool)

    conn.fetchrow.side_effect = [
        None,  # get_today_log returns None
        {"avg_mood": 3.5, "avg_energy": 3.0, "avg_stress": 2.5, "log_count": 5},
    ]

    result = await manager.get_recommendation(123)
    assert result["has_data"] is True
    assert result["source"] == "average"
    assert result["recommended_minutes"] == 25  # standard
    assert result["session_type"] == "standard"
