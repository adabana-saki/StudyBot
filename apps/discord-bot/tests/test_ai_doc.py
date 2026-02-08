"""AIドキュメント解析のテスト"""

import json
from unittest.mock import AsyncMock, patch

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


# --- クイズ生成テスト ---


@pytest.mark.asyncio
async def test_generate_quiz_success(ai_manager):
    """クイズ生成成功テスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0  # no rate limit

    quiz_json = json.dumps(
        [
            {
                "question": "Pythonのリストは？",
                "choices": ["A: 配列", "B: 辞書", "C: セット", "D: タプル"],
                "answer": "A",
                "explanation": "リストは順序付きの配列です。",
            },
        ]
    )

    with patch("studybot.managers.ai_doc_manager.call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = quiz_json

        result = await manager.generate_quiz(
            user_id=123,
            username="Test",
            file_content=b"Python list tutorial",
            filename="test.txt",
            count=1,
        )

    assert "questions" in result
    assert len(result["questions"]) == 1
    assert result["questions"][0]["answer"] == "A"


@pytest.mark.asyncio
async def test_generate_quiz_with_code_fences(ai_manager):
    """マークダウンコードフェンス付きクイズ生成テスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    quiz_response = (
        '```json\n[{"question": "Q1", '
        '"choices": ["A: a", "B: b", "C: c", "D: d"], '
        '"answer": "A", "explanation": "E1"}]\n```'
    )

    with patch("studybot.managers.ai_doc_manager.call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = quiz_response

        result = await manager.generate_quiz(
            user_id=123,
            username="Test",
            file_content=b"test content",
            filename="test.txt",
        )

    assert "questions" in result
    assert len(result["questions"]) == 1


@pytest.mark.asyncio
async def test_generate_quiz_rate_limited(ai_manager):
    """クイズ生成レート制限テスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 10  # daily limit reached

    result = await manager.generate_quiz(
        user_id=123,
        username="Test",
        file_content=b"test",
        filename="test.txt",
    )

    assert "error" in result
    assert "使用制限" in result["error"]


@pytest.mark.asyncio
async def test_generate_quiz_unsupported_file(ai_manager):
    """サポート外ファイルでのクイズ生成"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    result = await manager.generate_quiz(
        user_id=123,
        username="Test",
        file_content=b"data",
        filename="test.xlsx",
    )

    assert "error" in result


@pytest.mark.asyncio
async def test_generate_quiz_ai_failure(ai_manager):
    """AI失敗時のクイズ生成"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    with patch("studybot.managers.ai_doc_manager.call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = None

        result = await manager.generate_quiz(
            user_id=123,
            username="Test",
            file_content=b"test content",
            filename="test.txt",
        )

    assert "error" in result


@pytest.mark.asyncio
async def test_generate_quiz_invalid_json(ai_manager):
    """不正なJSON応答でのクイズ生成"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    with patch("studybot.managers.ai_doc_manager.call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = "これはJSONではありません"

        result = await manager.generate_quiz(
            user_id=123,
            username="Test",
            file_content=b"test content",
            filename="test.txt",
        )

    assert "error" in result


# --- 質問テスト ---


@pytest.mark.asyncio
async def test_ask_question_success(ai_manager):
    """質問成功テスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    with patch("studybot.managers.ai_doc_manager.call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = "Pythonのリストはミュータブルな順序付きコレクションです。"

        result = await manager.ask_question(
            user_id=123,
            username="Test",
            file_content=b"Python list tutorial",
            filename="test.txt",
            question="リストとは何ですか？",
        )

    assert "answer" in result
    assert "リスト" in result["answer"]


@pytest.mark.asyncio
async def test_ask_question_rate_limited(ai_manager):
    """質問レート制限テスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 10

    result = await manager.ask_question(
        user_id=123,
        username="Test",
        file_content=b"test",
        filename="test.txt",
        question="何ですか？",
    )

    assert "error" in result
    assert "使用制限" in result["error"]


@pytest.mark.asyncio
async def test_ask_question_ai_failure(ai_manager):
    """AI失敗時の質問"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    with patch("studybot.managers.ai_doc_manager.call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = None

        result = await manager.ask_question(
            user_id=123,
            username="Test",
            file_content=b"test content",
            filename="test.txt",
            question="何ですか？",
        )

    assert "error" in result


# --- 概念説明テスト ---


@pytest.mark.asyncio
async def test_explain_concept_success(ai_manager):
    """概念説明成功テスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    with patch("studybot.managers.ai_doc_manager.call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = "再帰とは、関数が自分自身を呼び出すプログラミング技法です。"

        result = await manager.explain_concept(
            user_id=123,
            username="Test",
            concept="再帰",
        )

    assert "explanation" in result
    assert "再帰" in result["explanation"]


@pytest.mark.asyncio
async def test_explain_concept_rate_limited(ai_manager):
    """概念説明レート制限テスト"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 10

    result = await manager.explain_concept(
        user_id=123,
        username="Test",
        concept="再帰",
    )

    assert "error" in result
    assert "使用制限" in result["error"]


@pytest.mark.asyncio
async def test_explain_concept_ai_failure(ai_manager):
    """AI失敗時の概念説明"""
    manager, conn = ai_manager

    conn.execute.return_value = None
    conn.fetchval.return_value = 0

    with patch("studybot.managers.ai_doc_manager.call_openai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = None

        result = await manager.explain_concept(
            user_id=123,
            username="Test",
            concept="再帰",
        )

    assert "error" in result
