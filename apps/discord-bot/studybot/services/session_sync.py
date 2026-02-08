"""クロスプラットフォームセッション同期サービス"""

import json
import logging
from datetime import UTC, datetime, timedelta

from studybot.repositories.session_sync_repository import SessionSyncRepository
from studybot.services.redis_client import RedisClient

logger = logging.getLogger(__name__)


class SessionSyncService:
    """DB + Redis によるセッション状態同期"""

    def __init__(self, db_pool, redis_client: RedisClient | None = None) -> None:
        self.repository = SessionSyncRepository(db_pool)
        self.redis = redis_client

    async def register_session(
        self,
        user_id: int,
        username: str,
        session_type: str,
        source: str,
        duration_minutes: int,
        topic: str = "",
        session_ref_id: int | None = None,
    ) -> dict:
        """セッションを登録（DB + Redis）"""
        await self.repository.ensure_user(user_id, username)

        # 既存セッションを終了
        await self.repository.end_user_sessions(user_id)

        end_time = datetime.now(UTC) + timedelta(minutes=duration_minutes)

        session_id = await self.repository.create_session(
            user_id=user_id,
            session_type=session_type,
            source_platform=source,
            duration_minutes=duration_minutes,
            end_time=end_time,
            topic=topic,
            session_ref_id=session_ref_id,
        )

        # Redis にセッション状態を保存
        if self.redis:
            session_data = {
                "session_id": session_id,
                "session_type": session_type,
                "source": source,
                "topic": topic,
                "end_time": end_time.isoformat(),
                "state": "active",
            }
            ttl = duration_minutes * 60 + 300  # + 5分バッファ
            await self.redis.set(
                f"session:{user_id}",
                json.dumps(session_data),
                ex=ttl,
            )

        return {
            "session_id": session_id,
            "session_type": session_type,
            "source": source,
            "topic": topic,
            "end_time": end_time.isoformat(),
            "duration_minutes": duration_minutes,
        }

    async def end_session(self, user_id: int) -> dict:
        """セッションを終了"""
        session = await self.repository.get_active_session(user_id)
        if not session:
            return {"error": "アクティブなセッションがありません"}

        await self.repository.end_session(session["id"])

        # Redis からも削除
        if self.redis:
            await self.redis.delete(f"session:{user_id}")

        return {
            "session_id": session["id"],
            "session_type": session["session_type"],
            "ended": True,
        }

    async def get_active_session(self, user_id: int) -> dict | None:
        """アクティブセッションを取得（Redis優先）"""
        if self.redis:
            cached = await self.redis.get(f"session:{user_id}")
            if cached:
                data = json.loads(cached)
                # 期限切れチェック
                end = datetime.fromisoformat(data["end_time"])
                if end > datetime.now(UTC):
                    remaining = (end - datetime.now(UTC)).total_seconds()
                    data["remaining_seconds"] = int(remaining)
                    return data

        # DB フォールバック
        return await self.repository.get_active_session(user_id)

    async def get_all_active(self) -> list[dict]:
        """全アクティブセッションを取得"""
        return await self.repository.get_active_sessions()

    async def cleanup_expired(self) -> int:
        """期限切れセッションをクリーンアップ"""
        return await self.repository.cleanup_expired()
