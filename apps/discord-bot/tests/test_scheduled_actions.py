"""スケジュールアクション Cog のテスト"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from studybot.cogs.scheduled_actions import ScheduledActionsCog
from studybot.config.constants import COLORS


@pytest.fixture
def cog(mock_bot):
    """ScheduledActionsCog インスタンス"""
    return ScheduledActionsCog(mock_bot)


# ---- send_dm ----


@pytest.mark.asyncio
async def test_execute_send_dm(cog):
    """DM送信: ユーザーにEmbed付きDMを送信"""
    mock_user = AsyncMock()
    cog.bot.get_user.return_value = mock_user

    result = await cog._execute_action(
        {
            "action_type": "send_dm",
            "action_data": {"user_id": 123456789, "message": "テストメッセージ"},
        }
    )

    assert result == "dm_sent"
    mock_user.send.assert_awaited_once()
    embed = mock_user.send.call_args.kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert "テストメッセージ" in embed.description
    assert embed.color.value == COLORS.get("primary", 0x5865F2)


@pytest.mark.asyncio
async def test_execute_send_dm_missing_user(cog):
    """DM送信: user_id/message不足で失敗"""
    # user_id 欠落
    result = await cog._execute_action(
        {
            "action_type": "send_dm",
            "action_data": {"message": "テスト"},
        }
    )
    assert result == "missing user_id or message"

    # message 欠落
    result = await cog._execute_action(
        {
            "action_type": "send_dm",
            "action_data": {"user_id": 123456789},
        }
    )
    assert result == "missing user_id or message"


# ---- create_challenge ----


@pytest.mark.asyncio
async def test_execute_create_challenge(cog):
    """チャレンジ作成: challenge_cogのmanager経由で作成"""
    mock_challenge_cog = MagicMock()
    mock_challenge_cog.manager = MagicMock()
    mock_challenge_cog.manager.create_challenge = AsyncMock(return_value={"id": 42})
    cog.bot.get_cog.return_value = mock_challenge_cog

    result = await cog._execute_action(
        {
            "action_type": "create_challenge",
            "action_data": {
                "creator_id": 111,
                "guild_id": 222,
                "name": "テストチャレンジ",
                "description": "説明",
                "goal_type": "study_minutes",
                "goal_target": 600,
                "duration_days": 7,
            },
        }
    )

    assert result == "challenge_created: 42"
    mock_challenge_cog.manager.create_challenge.assert_awaited_once_with(
        creator_id=111,
        guild_id=222,
        name="テストチャレンジ",
        description="説明",
        goal_type="study_minutes",
        goal_target=600,
        duration_days=7,
    )


@pytest.mark.asyncio
async def test_execute_create_challenge_no_cog(cog):
    """チャレンジ作成: ChallengeCog未ロード"""
    cog.bot.get_cog.return_value = None

    result = await cog._execute_action(
        {
            "action_type": "create_challenge",
            "action_data": {"name": "テスト"},
        }
    )

    assert result == "challenge_cog_not_loaded"


# ---- announce ----


@pytest.mark.asyncio
async def test_execute_announce(cog):
    """アナウンス: チャンネルにEmbed送信"""
    mock_channel = AsyncMock()
    cog.bot.get_channel.return_value = mock_channel

    result = await cog._execute_action(
        {
            "action_type": "announce",
            "action_data": {
                "channel_id": 555666777,
                "title": "テストタイトル",
                "body": "テスト本文",
            },
        }
    )

    assert result == "announced"
    mock_channel.send.assert_awaited_once()
    embed = mock_channel.send.call_args.kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert "テストタイトル" in embed.title
    assert "テスト本文" in embed.description


@pytest.mark.asyncio
async def test_execute_announce_no_channel(cog):
    """アナウンス: channel_id 欠落"""
    result = await cog._execute_action(
        {
            "action_type": "announce",
            "action_data": {"title": "テスト", "body": "本文"},
        }
    )

    assert result == "missing channel_id"


# ---- unknown action ----


@pytest.mark.asyncio
async def test_execute_unknown_action(cog):
    """不明なアクションタイプ"""
    result = await cog._execute_action(
        {
            "action_type": "foo",
            "action_data": {},
        }
    )

    assert result == "unknown action_type: foo"
