"""データベース接続管理"""

import logging

import asyncpg

from studybot.config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """asyncpg接続プール管理 + テーブル自動作成"""

    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def initialize(self) -> bool:
        """データベース接続とスキーマ初期化"""
        try:
            db_url = settings.database_url_fixed
            if not db_url:
                logger.error("DATABASE_URL が設定されていません")
                return False

            self.pool = await asyncpg.create_pool(
                db_url,
                min_size=settings.DB_POOL_MIN_SIZE,
                max_size=settings.DB_POOL_MAX_SIZE,
                command_timeout=settings.DB_COMMAND_TIMEOUT,
            )

            logger.info("データベース接続成功")
            await self._create_tables()
            return True

        except Exception as e:
            logger.error(f"データベース初期化失敗: {e}")
            return False

    async def _create_tables(self) -> None:
        """テーブル自動作成（IF NOT EXISTS）"""
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    topic VARCHAR(200) DEFAULT '',
                    work_minutes INT DEFAULT 25,
                    break_minutes INT DEFAULT 5,
                    state VARCHAR(20) DEFAULT 'idle',
                    started_at TIMESTAMP,
                    paused_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    total_work_seconds INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS study_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    topic VARCHAR(200) DEFAULT '',
                    duration_minutes INT NOT NULL,
                    source VARCHAR(20) DEFAULT 'manual',
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS todos (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    title VARCHAR(300) NOT NULL,
                    priority INT DEFAULT 2,
                    status VARCHAR(20) DEFAULT 'pending',
                    deadline TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_levels (
                    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                    xp INT DEFAULT 0,
                    level INT DEFAULT 1,
                    streak_days INT DEFAULT 0,
                    last_study_date DATE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS xp_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    amount INT NOT NULL,
                    reason VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_stats (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    period VARCHAR(20) NOT NULL,
                    period_start DATE NOT NULL,
                    total_minutes INT DEFAULT 0,
                    session_count INT DEFAULT 0,
                    tasks_completed INT DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, guild_id, period, period_start)
                );

                CREATE TABLE IF NOT EXISTS level_milestones (
                    level INT PRIMARY KEY,
                    badge VARCHAR(50),
                    role_name VARCHAR(100),
                    description VARCHAR(200)
                );

                CREATE TABLE IF NOT EXISTS ai_document_summaries (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    file_hash VARCHAR(64) NOT NULL,
                    detail_level VARCHAR(20) DEFAULT 'medium',
                    summary_type VARCHAR(20) NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_hash, detail_level, summary_type)
                );

                CREATE TABLE IF NOT EXISTS phone_nudges (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL UNIQUE REFERENCES users(user_id),
                    webhook_url TEXT,
                    enabled BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS nudge_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    event_type VARCHAR(50) NOT NULL,
                    message TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # インデックス作成
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pomodoro_user
                    ON pomodoro_sessions(user_id, state);
                CREATE INDEX IF NOT EXISTS idx_study_logs_user_date
                    ON study_logs(user_id, logged_at);
                CREATE INDEX IF NOT EXISTS idx_study_logs_guild
                    ON study_logs(guild_id, logged_at);
                CREATE INDEX IF NOT EXISTS idx_todos_user_status
                    ON todos(user_id, status);
                CREATE INDEX IF NOT EXISTS idx_xp_transactions_user
                    ON xp_transactions(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_user_stats_lookup
                    ON user_stats(user_id, guild_id, period);
                CREATE INDEX IF NOT EXISTS idx_ai_summaries_hash
                    ON ai_document_summaries(file_hash);
                """
            )

            # デフォルトマイルストーン挿入
            await conn.execute(
                """
                INSERT INTO level_milestones (level, badge, role_name, description)
                VALUES
                    (1,  '🌱', '初心者',       'StudyBot を始めました！'),
                    (5,  '📚', '学習者',       '着実に成長中！'),
                    (10, '🎓', '努力家',       '二桁レベル到達！'),
                    (20, '⭐', 'スター学習者', '圧倒的な継続力！'),
                    (30, '🏆', 'マスター',     '学習の達人！'),
                    (50, '💎', 'レジェンド',   '伝説の学習者！'),
                    (100,'👑', 'グランドマスター', '頂点に到達！')
                ON CONFLICT (level) DO NOTHING;
                """
            )

            logger.info("テーブル作成完了")

    async def close(self) -> None:
        """接続プールを閉じる"""
        if self.pool:
            await self.pool.close()
            logger.info("データベース接続を閉じました")
