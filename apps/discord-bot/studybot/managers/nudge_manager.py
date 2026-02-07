"""スマホ通知 ビジネスロジック"""

import logging

import aiohttp

from studybot.repositories.nudge_repository import NudgeRepository

logger = logging.getLogger(__name__)


class NudgeManager:
    """スマホ通知の管理"""

    def __init__(self, db_pool) -> None:
        self.repository = NudgeRepository(db_pool)

    async def setup_webhook(self, user_id: int, username: str, webhook_url: str) -> dict:
        """Webhook URLを設定"""
        await self.repository.ensure_user(user_id, username)

        # URL簡易バリデーション
        if not webhook_url.startswith(("http://", "https://")):
            return {"error": "URLは http:// または https:// で始まる必要があります。"}

        await self.repository.upsert_config(user_id, webhook_url)
        return {"success": True}

    async def toggle(self, user_id: int, enabled: bool) -> bool:
        """通知のON/OFF切り替え"""
        return await self.repository.toggle_enabled(user_id, enabled)

    async def send_nudge(self, user_id: int, event_type: str, message: str) -> bool:
        """Webhook通知を送信"""
        config = await self.repository.get_nudge_config(user_id)
        if not config or not config.get("enabled") or not config.get("webhook_url"):
            return False

        try:
            payload = {
                "content": message,
                "username": "StudyBot",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config["webhook_url"],
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    success = resp.status < 400

            if success:
                await self.repository.add_history(user_id, event_type, message)

            return success

        except Exception as e:
            logger.error(f"Nudge送信エラー (user={user_id}): {e}")
            return False

    async def get_config(self, user_id: int) -> dict | None:
        """現在の設定を取得"""
        return await self.repository.get_nudge_config(user_id)
