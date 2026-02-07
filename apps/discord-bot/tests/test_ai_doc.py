"""AIドキュメント解析のテスト"""

import pytest

from studybot.managers.ai_doc_manager import AIDocManager


@pytest.fixture
def ai_manager(mock_db_pool):
    pool, conn = mock_db_pool
    manager = AIDocManager(pool)
    return manager, conn


@pytest.mark.asyncio
async def test_extract_text_txt(ai_manager):
    """テキストファイルからの抽出"""
    manager, conn = ai_manager

    content = b"Hello, World!"
    result = await manager._extract_text(content, "test.txt")
    assert result == "Hello, World!"


@pytest.mark.asyncio
async def test_extract_text_unsupported(ai_manager):
    """サポート外ファイル"""
    manager, conn = ai_manager

    result = await manager._extract_text(b"data", "test.xlsx")
    assert result is None


@pytest.mark.asyncio
async def test_summarize_rate_limited(ai_manager):
    """レート制限テスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 10  # daily limit reached

    result = await manager.summarize(
        user_id=123,
        username="Test",
        file_content=b"test",
        filename="test.txt",
    )

    assert "error" in result
    assert "使用制限" in result["error"]


@pytest.mark.asyncio
async def test_summarize_cached(ai_manager):
    """キャッシュヒットテスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0  # no rate limit
    conn.fetchrow.return_value = {"summary": "キャッシュされた要約"}

    result = await manager.summarize(
        user_id=123,
        username="Test",
        file_content=b"test content",
        filename="test.txt",
        detail_level="medium",
    )

    assert result["cached"] is True
    assert result["summary"] == "キャッシュされた要約"


@pytest.mark.asyncio
async def test_summarize_empty_file(ai_manager):
    """空ファイルのエラー"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    result = await manager.summarize(
        user_id=123,
        username="Test",
        file_content=b"",
        filename="test.txt",
    )

    assert "error" in result


@pytest.mark.asyncio
async def test_extract_pdf_error(ai_manager):
    """PDF抽出エラー"""
    manager, conn = ai_manager

    result = manager._extract_pdf(b"not a pdf")
    assert result is None


def test_detail_prompts():
    """詳細度プロンプトが定義されていること"""
    from studybot.managers.ai_doc_manager import DETAIL_PROMPTS

    assert "brief" in DETAIL_PROMPTS
    assert "medium" in DETAIL_PROMPTS
    assert "detailed" in DETAIL_PROMPTS
