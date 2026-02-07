"""StudyBot API - FastAPI バックエンド"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import close_pool, init_pool
from api.routes import achievements, auth, flashcards, leaderboard, stats, wellness

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
    yield
    await close_pool()
    logger.info("APIシャットダウン完了")


app = FastAPI(
    title="StudyBot API",
    description="AI搭載学習支援Discord Bot のWeb API",
    version="2.0.0",
    lifespan=lifespan,
)

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


@app.get("/")
async def root():
    return {"name": "StudyBot API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
