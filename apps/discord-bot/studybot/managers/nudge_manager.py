"""スマホ通知 ビジネスロジック"""

import logging
from datetime import UTC, datetime, timedelta

import aiohttp

from studybot.config.constants import COIN_REWARDS, NUDGE_LEVELS
from studybot.repositories.nudge_repository import NudgeRepository

logger = logging.getLogger(__name__)


class NudgeManager:
    """スマホ通知の管理"""

    def __init__(self, db_pool) -> None:
        self.repository = NudgeRepository(db_pool)
        self.active_locks: dict[int, dict] = {}

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

    async def start_lock(
        self, user_id: int, username: str, duration_minutes: int, coins_bet: int = 0
    ) -> dict:
        """フォーカスロックを開始"""
        # 既存のアクティブロックをチェック
        if user_id in self.active_locks:
            return {"error": "既にアクティブなロックがあります。"}

        existing = await self.repository.get_active_lock(user_id)
        if existing:
            return {"error": "既にアクティブなロックがあります。"}

        # コインベットのバリデーション
        lock_config = NUDGE_LEVELS["lock"]
        if coins_bet > 0 and (
            coins_bet < lock_config["coin_bet_min"] or coins_bet > lock_config["coin_bet_max"]
        ):
            return {
                "error": (
                    f"コインベットは{lock_config['coin_bet_min']}〜"
                    f"{lock_config['coin_bet_max']}の範囲で指定してください。"
                ),
            }

        await self.repository.ensure_user(user_id, username)
        session = await self.repository.create_lock_session(
            user_id, "lock", duration_minutes, coins_bet
        )

        end_time = datetime.now(UTC) + timedelta(minutes=duration_minutes)
        self.active_locks[user_id] = {
            "session_id": session["id"],
            "end_time": end_time,
            "coins_bet": coins_bet,
            "lock_type": "lock",
        }

        return {
            "session_id": session["id"],
            "duration": duration_minutes,
            "coins_bet": coins_bet,
            "end_time": end_time,
        }

    async def start_shield(self, user_id: int, username: str, duration_minutes: int) -> dict:
        """フォーカスシールドを開始"""
        # 既存のアクティブロックをチェック
        if user_id in self.active_locks:
            return {"error": "既にアクティブなロックがあります。"}

        existing = await self.repository.get_active_lock(user_id)
        if existing:
            return {"error": "既にアクティブなロックがあります。"}

        # 時間のバリデーション
        shield_config = NUDGE_LEVELS["shield"]
        if (
            duration_minutes < shield_config["min_duration"]
            or duration_minutes > shield_config["max_duration"]
        ):
            return {
                "error": (
                    f"シールドの時間は{shield_config['min_duration']}〜"
                    f"{shield_config['max_duration']}分の範囲で指定してください。"
                ),
            }

        await self.repository.ensure_user(user_id, username)
        session = await self.repository.create_lock_session(user_id, "shield", duration_minutes)

        end_time = datetime.now(UTC) + timedelta(minutes=duration_minutes)
        self.active_locks[user_id] = {
            "session_id": session["id"],
            "end_time": end_time,
            "coins_bet": 0,
            "lock_type": "shield",
            "last_nudge_time": datetime.now(UTC),
        }

        return {
            "session_id": session["id"],
            "duration": duration_minutes,
            "end_time": end_time,
        }

    async def break_lock(self, user_id: int) -> dict:
        """ロックを中断"""
        lock_info = self.active_locks.get(user_id)
        if not lock_info:
            # DBからも確認
            existing = await self.repository.get_active_lock(user_id)
            if not existing:
                return {"error": "アクティブなロックがありません。"}
            lock_info = {
                "session_id": existing["id"],
                "coins_bet": existing.get("coins_bet", 0),
            }

        session = await self.repository.break_lock(lock_info["session_id"])
        coins_lost = lock_info.get("coins_bet", 0)
        self.active_locks.pop(user_id, None)

        return {"broken": True, "coins_lost": coins_lost, "session": session}

    async def complete_lock(self, user_id: int) -> dict:
        """ロックを完了"""
        lock_info = self.active_locks.get(user_id)
        if not lock_info:
            existing = await self.repository.get_active_lock(user_id)
            if not existing:
                return {"error": "アクティブなロックがありません。"}
            lock_info = {
                "session_id": existing["id"],
                "coins_bet": existing.get("coins_bet", 0),
            }

        session = await self.repository.complete_lock(lock_info["session_id"])
        coins_bet = lock_info.get("coins_bet", 0)
        coins_earned = COIN_REWARDS["lock_complete"]
        self.active_locks.pop(user_id, None)

        return {
            "completed": True,
            "coins_earned": coins_earned,
            "coins_returned": coins_bet,
            "session": session,
        }

    async def get_lock_status(self, user_id: int) -> dict | None:
        """アクティブロックのステータスを取得"""
        lock_info = self.active_locks.get(user_id)
        if not lock_info:
            existing = await self.repository.get_active_lock(user_id)
            if not existing:
                return None
            # DBから復元
            end_time = existing["started_at"] + timedelta(minutes=existing["duration_minutes"])
            lock_info = {
                "session_id": existing["id"],
                "end_time": end_time,
                "coins_bet": existing.get("coins_bet", 0),
                "lock_type": existing["lock_type"],
            }

        now = datetime.now(UTC)
        remaining = lock_info["end_time"] - now
        remaining_seconds = max(0, int(remaining.total_seconds()))

        return {
            "session_id": lock_info["session_id"],
            "lock_type": lock_info.get("lock_type", "lock"),
            "coins_bet": lock_info.get("coins_bet", 0),
            "end_time": lock_info["end_time"],
            "remaining_seconds": remaining_seconds,
            "remaining_minutes": remaining_seconds // 60,
        }

    async def check_locks(self) -> list[dict]:
        """期限切れロックをチェックして完了リストを返す"""
        now = datetime.now(UTC)
        completed = []

        expired_users = [
            user_id for user_id, info in self.active_locks.items() if now >= info["end_time"]
        ]

        for user_id in expired_users:
            result = await self.complete_lock(user_id)
            result["user_id"] = user_id
            completed.append(result)

        return completed
