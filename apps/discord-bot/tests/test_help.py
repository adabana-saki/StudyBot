"""ヘルプCogのテスト"""

import pytest

from studybot.cogs.help import COMMAND_HELP, HelpCog


def test_command_help_has_all_categories():
    """全カテゴリにコマンドが定義されている"""
    from studybot.config.constants import HELP_CATEGORIES

    for key in HELP_CATEGORIES:
        assert key in COMMAND_HELP, f"カテゴリ '{key}' がCOMMAND_HELPにありません"
        assert len(COMMAND_HELP[key]) > 0, f"カテゴリ '{key}' にコマンドがありません"


def test_command_help_format():
    """コマンドヘルプのフォーマットが正しい"""
    for _category, commands in COMMAND_HELP.items():
        for cmd, desc in commands:
            assert cmd.startswith("/"), f"コマンド '{cmd}' が / で始まっていません"
            assert len(desc) > 0, f"コマンド '{cmd}' の説明が空です"


@pytest.mark.asyncio
async def test_help_cog_init(mock_bot):
    """HelpCogの初期化テスト"""
    cog = HelpCog(mock_bot)
    assert cog.bot == mock_bot


@pytest.mark.asyncio
async def test_help_command(mock_bot, mock_interaction):
    """ヘルプコマンド実行テスト"""
    cog = HelpCog(mock_bot)
    await cog.help_command.callback(cog, mock_interaction)
    mock_interaction.response.send_message.assert_called_once()
