"""ソーシャル通知のテスト"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from studybot.cogs.social_notify import SocialNotifyCog


@pytest.fixture
def social_cog(mock_bot):
    cog = SocialNotifyCog(mock_bot)
    return cog


@pytest.mark.asyncio
async def test_handle_reaction_sends_dm(social_cog, mock_bot):
    """リアクション通知がDMを送信する"""
    target_user = AsyncMock()
    mock_bot.get_user = MagicMock(return_value=target_user)

    data = {
        "type": "social_reaction",
        "data": {
            "event_id": 1,
            "target_user_id": 100,
            "actor_user_id": 200,
            "actor_username": "Alice",
            "reaction_type": "fire",
        },
    }

    await social_cog._handle_social_event(data)
    target_user.send.assert_called_once()
    embed = target_user.send.call_args[1]["embed"]
    assert "Alice" in embed.description
    assert "🔥" in embed.title


@pytest.mark.asyncio
async def test_handle_comment_sends_dm(social_cog, mock_bot):
    """コメント通知がDMを送信する"""
    target_user = AsyncMock()
    mock_bot.get_user = MagicMock(return_value=target_user)

    data = {
        "type": "social_comment",
        "data": {
            "event_id": 2,
            "target_user_id": 100,
            "actor_user_id": 200,
            "actor_username": "Bob",
            "body": "すごい！頑張ってるね！",
        },
    }

    await social_cog._handle_social_event(data)
    target_user.send.assert_called_once()
    embed = target_user.send.call_args[1]["embed"]
    assert "Bob" in embed.description
    assert "コメント" in embed.title


@pytest.mark.asyncio
async def test_no_self_notification(social_cog, mock_bot):
    """自分自身へのリアクションでは通知しない"""
    target_user = AsyncMock()
    mock_bot.get_user = MagicMock(return_value=target_user)

    data = {
        "type": "social_reaction",
        "data": {
            "event_id": 3,
            "target_user_id": 100,
            "actor_user_id": 100,
            "actor_username": "Self",
            "reaction_type": "applaud",
        },
    }

    await social_cog._handle_social_event(data)
    target_user.send.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limit_prevents_duplicate_notification(social_cog, mock_bot):
    """同じイベントへの通知は1時間に1回"""
    target_user = AsyncMock()
    mock_bot.get_user = MagicMock(return_value=target_user)

    data = {
        "type": "social_reaction",
        "data": {
            "event_id": 5,
            "target_user_id": 100,
            "actor_user_id": 200,
            "actor_username": "Alice",
            "reaction_type": "applaud",
        },
    }

    await social_cog._handle_social_event(data)
    assert target_user.send.call_count == 1

    # Second call should be rate-limited
    await social_cog._handle_social_event(data)
    assert target_user.send.call_count == 1
