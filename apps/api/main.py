"""StudyBot API - FastAPI バックエンド"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import close_pool, init_pool
from api.middleware.error_handler import setup_error_handlers
from api.middleware.rate_limiter import RateLimitMiddleware
from api.middleware.security_headers import SecurityHeadersMiddleware
from api.routes import (
    achievements,
    activity,
    admin,
    auth,
    buddy,
    challenges,
    events,
    flashcards,
    focus,
    insights,
    leaderboard,
    mobile_auth,
    notifications,
    plans,
    profile,
    server,
    sessions,
    shop,
    stats,
    todos,
    wellness,
)
from api.services.event_stream import close_event_stream, init_event_stream
from api.services.redis_client import close_redis, init_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("studybot-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    logger.info("API起動中...")
    await init_pool()
    logger.info("データベース接続完了")

    # Redis + EventStream初期化
    try:
        redis_conn = await init_redis(settings.REDIS_URL)
        await init_event_stream(redis_conn)
        logger.info("Redis + EventStream初期化完了")
    except Exception as e:
        logger.warning(f"Redis初期化失敗（リアルタイム機能無効）: {e}")

    yield

    await close_event_stream()
    await close_redis()
    await close_pool()
    logger.info("APIシャットダウン完了")


app = FastAPI(
    title="StudyBot API",
    description="AI搭載学習支援Discord Bot のWeb API",
    version="2.0.0",
    lifespan=lifespan,
)

# グローバルエラーハンドラ
setup_error_handlers(app)

# セキュリティミドルウェア
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, rate_limit=60, window=60)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.WEB_BASE_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(leaderboard.router)
app.include_router(achievements.router)
app.include_router(flashcards.router)
app.include_router(wellness.router)
app.include_router(focus.router)
app.include_router(notifications.router)
# Phase 3
app.include_router(mobile_auth.router)
app.include_router(shop.router)
app.include_router(todos.router)
app.include_router(plans.router)
app.include_router(profile.router)
app.include_router(server.router)
app.include_router(admin.router)
# Phase 5
app.include_router(events.router)
app.include_router(activity.router)
app.include_router(buddy.router)
app.include_router(challenges.router)
app.include_router(sessions.router)
app.include_router(insights.router)


@app.get("/")
async def root():
    return {"name": "StudyBot API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
