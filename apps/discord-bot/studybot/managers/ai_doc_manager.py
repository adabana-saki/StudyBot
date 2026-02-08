"""AIドキュメント解析 ビジネスロジック"""

import hashlib
import io
import json
import logging
import re

from studybot.config.settings import settings
from studybot.repositories.ai_doc_repository import AIDocRepository
from studybot.services.openai_service import call_openai

logger = logging.getLogger(__name__)

DETAIL_PROMPTS = {
    "brief": "以下のテキストを3行以内で簡潔に要約してください。",
    "medium": "以下のテキストを段落ごとにわかりやすく要約してください。",
    "detailed": "以下のテキストを詳細に要約し、重要なポイントをすべて含めてください。",
}

KEYPOINT_PROMPT = (
    "以下のテキストから重要なポイントを箇条書きで抽出してください。"
    "各ポイントは簡潔に、しかし意味が伝わるようにしてください。"
)


class AIDocManager:
    """AIドキュメント解析の管理"""

    def __init__(self, db_pool) -> None:
        self.repository = AIDocRepository(db_pool)

    async def summarize(
        self,
        user_id: int,
        username: str,
        file_content: bytes,
        filename: str,
        detail_level: str = "medium",
    ) -> dict:
        """ファイルを要約"""
        await self.repository.ensure_user(user_id, username)

        # レート制限チェック
        usage = await self.repository.get_daily_usage_count(user_id)
        if usage >= settings.AI_DAILY_LIMIT:
            return {"error": f"1日の使用制限({settings.AI_DAILY_LIMIT}回)に達しました。"}

        # テキスト抽出
        text = await self._extract_text(file_content, filename)
        if not text:
            return {"error": "ファイルからテキストを抽出できませんでした。"}

        # ハッシュでキャッシュチェック
        file_hash = hashlib.sha256(file_content).hexdigest()
        cached = await self.repository.get_cached_summary(file_hash, detail_level, "summary")
        if cached:
            return {"summary": cached, "cached": True}

        # OpenAI APIで要約生成
        prompt = DETAIL_PROMPTS.get(detail_level, DETAIL_PROMPTS["medium"])
        summary = await call_openai(f"{prompt}\n\n{text[:8000]}", max_tokens=1024)
        if not summary:
            return {"error": "AI要約の生成に失敗しました。"}

        # キャッシュ保存
        await self.repository.save_summary(user_id, file_hash, detail_level, "summary", summary)

        return {"summary": summary, "cached": False}

    async def extract_keypoints(
        self,
        user_id: int,
        username: str,
        file_content: bytes,
        filename: str,
    ) -> dict:
        """キーポイントを抽出"""
        await self.repository.ensure_user(user_id, username)

        usage = await self.repository.get_daily_usage_count(user_id)
        if usage >= settings.AI_DAILY_LIMIT:
            return {"error": f"1日の使用制限({settings.AI_DAILY_LIMIT}回)に達しました。"}

        text = await self._extract_text(file_content, filename)
        if not text:
            return {"error": "ファイルからテキストを抽出できませんでした。"}

        file_hash = hashlib.sha256(file_content).hexdigest()
        cached = await self.repository.get_cached_summary(file_hash, "medium", "keypoints")
        if cached:
            return {"keypoints": cached, "cached": True}

        keypoints = await call_openai(f"{KEYPOINT_PROMPT}\n\n{text[:8000]}", max_tokens=800)
        if not keypoints:
            return {"error": "キーポイント抽出に失敗しました。"}

        await self.repository.save_summary(user_id, file_hash, "medium", "keypoints", keypoints)

        return {"keypoints": keypoints, "cached": False}

    async def _extract_text(self, content: bytes, filename: str) -> str | None:
        """ファイルからテキストを抽出"""
        lower = filename.lower()

        if lower.endswith(".pdf"):
            return self._extract_pdf(content)
        elif lower.endswith((".txt", ".md", ".py", ".js", ".java", ".c", ".cpp")):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return content.decode("shift_jis")
                except UnicodeDecodeError:
                    return None
        return None

    def _extract_pdf(self, content: bytes) -> str | None:
        """PDFからテキストを抽出"""
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(content))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n".join(text_parts) if text_parts else None
        except Exception as e:
            logger.error(f"PDF抽出エラー: {e}")
            return None

    async def generate_quiz(
        self,
        user_id: int,
        username: str,
        file_content: bytes,
        filename: str,
        count: int = 5,
    ) -> dict:
        """ファイルからクイズを生成"""
        await self.repository.ensure_user(user_id, username)

        usage = await self.repository.get_daily_usage_count(user_id)
        if usage >= settings.AI_DAILY_LIMIT:
            return {"error": f"1日の使用制限({settings.AI_DAILY_LIMIT}回)に達しました。"}

        text = await self._extract_text(file_content, filename)
        if not text:
            return {"error": "ファイルからテキストを抽出できませんでした。"}

        prompt = (
            f"以下のテキストから{count}問の4択クイズを生成してください。"
            "JSON形式で回答してください。"
            '形式: [{"question": "...", "choices": ["A: ...", "B: ...", "C: ...", "D: ..."], '
            '"answer": "A", "explanation": "..."}]'
            f"\n\n{text[:8000]}"
        )

        response = await call_openai(prompt, max_tokens=1500)
        if not response:
            return {"error": "クイズの生成に失敗しました。"}

        try:
            # マークダウンコードフェンスを除去
            cleaned = re.sub(r"```(?:json)?\s*", "", response)
            cleaned = cleaned.strip().rstrip("`")
            questions = json.loads(cleaned)
            return {"questions": questions}
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"クイズJSON解析エラー: {e}")
            return {"error": "クイズの解析に失敗しました。"}

    async def ask_question(
        self,
        user_id: int,
        username: str,
        file_content: bytes,
        filename: str,
        question: str,
    ) -> dict:
        """ドキュメントについて質問"""
        await self.repository.ensure_user(user_id, username)

        usage = await self.repository.get_daily_usage_count(user_id)
        if usage >= settings.AI_DAILY_LIMIT:
            return {"error": f"1日の使用制限({settings.AI_DAILY_LIMIT}回)に達しました。"}

        text = await self._extract_text(file_content, filename)
        if not text:
            return {"error": "ファイルからテキストを抽出できませんでした。"}

        prompt = (
            "以下のテキストの内容に基づいて質問に回答してください。\n\n"
            f"テキスト:\n{text[:8000]}\n\n"
            f"質問: {question}"
        )

        answer = await call_openai(prompt, max_tokens=1024)
        if not answer:
            return {"error": "回答の生成に失敗しました。"}

        return {"answer": answer}

    async def explain_concept(
        self,
        user_id: int,
        username: str,
        concept: str,
    ) -> dict:
        """概念を説明"""
        await self.repository.ensure_user(user_id, username)

        usage = await self.repository.get_daily_usage_count(user_id)
        if usage >= settings.AI_DAILY_LIMIT:
            return {"error": f"1日の使用制限({settings.AI_DAILY_LIMIT}回)に達しました。"}

        prompt = (
            f"「{concept}」について、学生にもわかりやすく丁寧に説明してください。"
            "必要に応じて具体例も含めてください。"
        )

        explanation = await call_openai(prompt, max_tokens=1500)
        if not explanation:
            return {"error": "説明の生成に失敗しました。"}

        return {"explanation": explanation}

