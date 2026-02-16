"""スマホ通知 ビジネスロジック"""

import asyncio
import ipaddress
import logging
import random
import socket
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import aiohttp

from studybot.config.constants import (
    CHALLENGE_DIFFICULTY,
    COIN_REWARDS,
    NUDGE_LEVELS,
    PENALTY_UNLOCK_RATE,
    TYPING_PHRASES,
    UNLOCK_LEVELS,
)
from studybot.repositories.lock_settings_repository import LockSettingsRepository
from studybot.repositories.nudge_repository import NudgeRepository

logger = logging.getLogger(__name__)


def _is_safe_url(url: str) -> bool:
    """Webhook URLがプライベート/予約済みIPを指さないことを検証（SSRF防止）"""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        addr = socket.getaddrinfo(hostname, None)[0][4][0]
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            return False
    except (socket.gaierror, ValueError):
        return False
    return True


class NudgeManager:
    """スマホ通知の管理"""

    def __init__(self, db_pool) -> None:
        self.repository = NudgeRepository(db_pool)
        self.lock_settings_repo = LockSettingsRepository(db_pool)
        self.active_locks: dict[int, dict] = {}
        self._lock = asyncio.Lock()

    async def setup_webhook(self, user_id: int, username: str, webhook_url: str) -> dict:
        """Webhook URLを設定"""
        await self.repository.ensure_user(user_id, username)

        # URL簡易バリデーション
        if not webhook_url.startswith(("http://", "https://")):
            return {"error": "URLは http:// または https:// で始まる必要があります。"}

        # SSRF防止: プライベートIPへのリクエストをブロック
        if not _is_safe_url(webhook_url):
            return {"error": "プライベートIPアドレスへのWebhookは許可されていません。"}

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
        self,
        user_id: int,
        username: str,
        duration_minutes: int,
        coins_bet: int = 0,
        unlock_level: int = 1,
        challenge_mode: str = "none",
    ) -> dict:
        """フォーカスロックを開始"""
        async with self._lock:
            # 既存のアクティブロックをチェック
            if user_id in self.active_locks:
                return {"error": "既にアクティブなロックがあります。"}

            existing = await self.repository.get_active_lock(user_id)
            if existing:
                return {"error": "既にアクティブなロックがあります。"}

            # アンロックレベルのバリデーション
            if unlock_level not in UNLOCK_LEVELS:
                return {"error": "アンロックレベルは1〜5の範囲で指定してください。"}

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
                user_id, "lock", duration_minutes, coins_bet, unlock_level
            )

            end_time = datetime.now(UTC) + timedelta(minutes=duration_minutes)
            self.active_locks[user_id] = {
                "session_id": session["id"],
                "end_time": end_time,
                "coins_bet": coins_bet,
                "lock_type": "lock",
                "unlock_level": unlock_level,
                "challenge_mode": challenge_mode,
            }

            result = {
                "session_id": session["id"],
                "duration": duration_minutes,
                "coins_bet": coins_bet,
                "end_time": end_time,
                "unlock_level": unlock_level,
                "challenge_mode": challenge_mode,
            }

            # レベル2: 開始時に確認コードをDM送信
            if unlock_level == 2:
                code = await self.generate_confirmation_code(user_id, session["id"])
                result["confirmation_code"] = code

            return result

    async def start_shield(self, user_id: int, username: str, duration_minutes: int) -> dict:
        """フォーカスシールドを開始"""
        async with self._lock:
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
                "unlock_level": 1,
                "last_nudge_time": datetime.now(UTC),
            }

            return {
                "session_id": session["id"],
                "duration": duration_minutes,
                "end_time": end_time,
            }

    async def break_lock(self, user_id: int) -> dict:
        """ロックを中断"""
        async with self._lock:
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

    async def _complete_lock_inner(self, user_id: int) -> dict:
        """ロック完了の内部実装（ロック取得済みの状態で呼ぶ）"""
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

    async def complete_lock(self, user_id: int) -> dict:
        """ロックを完了"""
        async with self._lock:
            return await self._complete_lock_inner(user_id)

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
                "unlock_level": existing.get("unlock_level", 1),
            }

        now = datetime.now(UTC)
        remaining = lock_info["end_time"] - now
        remaining_seconds = max(0, int(remaining.total_seconds()))

        return {
            "session_id": lock_info["session_id"],
            "lock_type": lock_info.get("lock_type", "lock"),
            "coins_bet": lock_info.get("coins_bet", 0),
            "unlock_level": lock_info.get("unlock_level", 1),
            "end_time": lock_info["end_time"],
            "remaining_seconds": remaining_seconds,
            "remaining_minutes": remaining_seconds // 60,
        }

    async def check_locks(self) -> list[dict]:
        """期限切れロックをチェックして完了リストを返す（レベル1のみ自動完了）"""
        async with self._lock:
            now = datetime.now(UTC)
            completed = []

            expired_users = [
                user_id
                for user_id, info in self.active_locks.items()
                if now >= info["end_time"] and info.get("unlock_level", 1) == 1
            ]

            for user_id in expired_users:
                result = await self._complete_lock_inner(user_id)
                result["user_id"] = user_id
                completed.append(result)

            return completed

    # --- 5段階アンロック関連 ---

    async def generate_confirmation_code(self, user_id: int, session_id: int) -> str:
        """レベル2: 確認コード(6桁数字)を生成してDM送信"""
        code = await self.lock_settings_repo.create_unlock_code(
            user_id, session_id, "confirmation", code_length=6
        )
        return code

    async def generate_dm_code(self, user_id: int, session_id: int) -> str:
        """レベル3: DMコード(8文字英数字)を生成"""
        code = await self.lock_settings_repo.create_unlock_code(
            user_id, session_id, "dm", code_length=8
        )
        return code

    async def generate_study_code(self, user_id: int, session_id: int) -> str:
        """レベル4: 学習完了コード(12文字英数字)を生成"""
        code = await self.lock_settings_repo.create_unlock_code(
            user_id, session_id, "study", code_length=12
        )
        return code

    async def verify_unlock_code(self, user_id: int, code: str) -> dict:
        """アンロックコードを検証してロック解除"""
        async with self._lock:
            lock_info = self.active_locks.get(user_id)
            if not lock_info:
                existing = await self.repository.get_active_lock(user_id)
                if not existing:
                    return {"error": "アクティブなロックがありません。"}
                lock_info = {
                    "session_id": existing["id"],
                    "coins_bet": existing.get("coins_bet", 0),
                    "unlock_level": existing.get("unlock_level", 1),
                }

            session_id = lock_info["session_id"]
            valid_code = await self.lock_settings_repo.get_valid_code(user_id, session_id, code)

            if not valid_code:
                return {
                    "error": "無効なコードです。コードが間違っているか、有効期限が切れています。"
                }

            # コードを使用済みにする
            await self.lock_settings_repo.use_code(valid_code["id"])

            # ロックを完了
            return await self._complete_lock_inner(user_id)

    async def penalty_unlock(self, user_id: int) -> dict:
        """レベル5: ペナルティ解除（全ベット+残高20%没収）"""
        async with self._lock:
            lock_info = self.active_locks.get(user_id)
            if not lock_info:
                existing = await self.repository.get_active_lock(user_id)
                if not existing:
                    return {"error": "アクティブなロックがありません。"}
                lock_info = {
                    "session_id": existing["id"],
                    "coins_bet": existing.get("coins_bet", 0),
                    "unlock_level": existing.get("unlock_level", 1),
                }

            if lock_info.get("unlock_level", 1) != 5:
                return {"error": "このロックはペナルティ解除に対応していません。"}

            coins_bet = lock_info.get("coins_bet", 0)

            # セッションを中断扱いにする
            await self.repository.break_lock(lock_info["session_id"])
            self.active_locks.pop(user_id, None)

            return {
                "penalty_unlocked": True,
                "coins_lost": coins_bet,
                "penalty_rate": PENALTY_UNLOCK_RATE,
            }

    # --- チャレンジ生成・検証 ---

    def generate_math_challenge(self, difficulty: int = 1) -> list[dict]:
        """計算チャレンジの問題リストを生成"""
        config = CHALLENGE_DIFFICULTY.get(difficulty, CHALLENGE_DIFFICULTY[1])
        problems = []
        for _ in range(config["problems"]):
            op = random.choice(config["ops"])
            a = random.randint(10 ** (config["min_digits"] - 1), 10 ** config["max_digits"] - 1)
            b = random.randint(10 ** (config["min_digits"] - 1), 10 ** config["max_digits"] - 1)
            # 整数除算の場合、割り切れるようにする
            if op == "//":
                b = max(b, 2)
                a = a * b  # a が b で割り切れるようにする
            expr = f"{a} {op} {b}"
            answer = a + b if op == "+" else a - b if op == "-" else a * b if op == "*" else a // b
            problems.append({"expression": expr, "answer": answer})
        return problems

    def generate_typing_challenge(self, difficulty: int = 1) -> list[str]:
        """タイピングチャレンジのフレーズを選出"""
        count = min(difficulty, len(TYPING_PHRASES))
        return random.sample(TYPING_PHRASES, count)

    def verify_math_challenge(self, problems: list[dict], answers: list[int]) -> dict:
        """計算チャレンジの回答を検証（全問正解で成功）"""
        if len(answers) != len(problems):
            return {"correct": False, "score": 0, "total": len(problems)}
        correct_count = sum(
            1 for p, a in zip(problems, answers) if p["answer"] == a
        )
        return {
            "correct": correct_count == len(problems),
            "score": correct_count,
            "total": len(problems),
        }

    def verify_typing_challenge(self, originals: list[str], typed: list[str]) -> dict:
        """タイピングチャレンジの回答を検証（完全一致判定+精度）"""
        if len(typed) != len(originals):
            return {"correct": False, "accuracy": 0.0, "total": len(originals)}
        matches = sum(1 for o, t in zip(originals, typed) if o == t)
        accuracy = matches / len(originals) if originals else 0.0
        return {
            "correct": matches == len(originals),
            "accuracy": round(accuracy * 100, 1),
            "total": len(originals),
            "matched": matches,
        }

    async def on_study_completed(self, user_id: int) -> str | None:
        """学習完了時のフック（レベル4用）。コードを返すかNone。"""
        lock_info = self.active_locks.get(user_id)
        if not lock_info:
            existing = await self.repository.get_active_lock(user_id)
            if not existing:
                return None
            lock_info = {
                "session_id": existing["id"],
                "unlock_level": existing.get("unlock_level", 1),
            }

        if lock_info.get("unlock_level") != 4:
            return None

        code = await self.generate_study_code(user_id, lock_info["session_id"])
        return code

    async def process_code_requests(self, bot) -> None:
        """保留中のコードリクエストを処理"""
        pending = await self.lock_settings_repo.get_pending_requests()

        for request in pending:
            user_id = request["user_id"]
            session_id = request["session_id"]
            unlock_level = request.get("unlock_level", 1)

            try:
                if unlock_level == 3:
                    code = await self.generate_dm_code(user_id, session_id)
                    user = bot.get_user(user_id) or await bot.fetch_user(user_id)
                    if user:
                        await user.send(
                            f"🔓 フォーカスロック解除コード: **{code}**\n（有効期限: 15分）"
                        )
                elif unlock_level == 4:
                    user = bot.get_user(user_id) or await bot.fetch_user(user_id)
                    if user:
                        await user.send(
                            "📚 学習セッションを完了するとアンロックコードが発行されます。\n"
                            "`/study log` または `/pomodoro` で学習を完了してください。"
                        )

                await self.lock_settings_repo.fulfill_request(request["id"])
            except Exception as e:
                logger.error(f"コードリクエスト処理エラー (user={user_id}): {e}")
