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

                -- Phase 2: Stream A - 仮想通貨 & ショップ
                CREATE TABLE IF NOT EXISTS virtual_currency (
                    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                    balance INT DEFAULT 0,
                    total_earned INT DEFAULT 0,
                    total_spent INT DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS shop_items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    category VARCHAR(30) NOT NULL,
                    price INT NOT NULL,
                    rarity VARCHAR(20) DEFAULT 'common',
                    emoji VARCHAR(10) DEFAULT '🎁',
                    metadata JSONB DEFAULT '{}',
                    active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    item_id INT NOT NULL REFERENCES shop_items(id),
                    quantity INT DEFAULT 1,
                    equipped BOOLEAN DEFAULT false,
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_id)
                );

                CREATE TABLE IF NOT EXISTS purchase_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    item_id INT NOT NULL REFERENCES shop_items(id),
                    price INT NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Phase 2: Stream A - スタディレイド
                CREATE TABLE IF NOT EXISTS study_raids (
                    id SERIAL PRIMARY KEY,
                    creator_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    topic VARCHAR(200) NOT NULL,
                    duration_minutes INT NOT NULL,
                    max_participants INT DEFAULT 10,
                    state VARCHAR(20) DEFAULT 'recruiting',
                    started_at TIMESTAMPTZ,
                    ended_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS raid_participants (
                    id SERIAL PRIMARY KEY,
                    raid_id INT NOT NULL REFERENCES study_raids(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    joined_at TIMESTAMPTZ DEFAULT NOW(),
                    completed BOOLEAN DEFAULT false,
                    UNIQUE(raid_id, user_id)
                );

                -- Phase 2: Stream A - 実績システム
                CREATE TABLE IF NOT EXISTS achievements (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    emoji VARCHAR(10) DEFAULT '🏅',
                    category VARCHAR(30) DEFAULT 'general',
                    target_value INT DEFAULT 1,
                    reward_coins INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_achievements (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    achievement_id INT NOT NULL REFERENCES achievements(id),
                    progress INT DEFAULT 0,
                    unlocked BOOLEAN DEFAULT false,
                    unlocked_at TIMESTAMP,
                    UNIQUE(user_id, achievement_id)
                );

                -- Phase 2: Stream B - フラッシュカード
                CREATE TABLE IF NOT EXISTS flashcard_decks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    name VARCHAR(100) NOT NULL,
                    description TEXT DEFAULT '',
                    card_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS flashcards (
                    id SERIAL PRIMARY KEY,
                    deck_id INT NOT NULL REFERENCES flashcard_decks(id) ON DELETE CASCADE,
                    front TEXT NOT NULL,
                    back TEXT NOT NULL,
                    easiness FLOAT DEFAULT 2.5,
                    interval INT DEFAULT 0,
                    repetitions INT DEFAULT 0,
                    next_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS flashcard_reviews (
                    id SERIAL PRIMARY KEY,
                    card_id INT NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    quality INT NOT NULL,
                    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Phase 2: Stream B - 学習プラン
                CREATE TABLE IF NOT EXISTS study_plans (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    subject VARCHAR(200) NOT NULL,
                    goal TEXT NOT NULL,
                    deadline DATE,
                    status VARCHAR(20) DEFAULT 'active',
                    ai_feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS plan_tasks (
                    id SERIAL PRIMARY KEY,
                    plan_id INT NOT NULL REFERENCES study_plans(id) ON DELETE CASCADE,
                    title VARCHAR(300) NOT NULL,
                    description TEXT DEFAULT '',
                    order_index INT DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'pending',
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Phase 2: Stream C - ウェルネス
                CREATE TABLE IF NOT EXISTS wellness_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    mood INT NOT NULL CHECK (mood BETWEEN 1 AND 5),
                    energy INT NOT NULL CHECK (energy BETWEEN 1 AND 5),
                    stress INT NOT NULL CHECK (stress BETWEEN 1 AND 5),
                    note TEXT DEFAULT '',
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Phase 2: Stream C - フォーカスセッション
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    duration_minutes INT NOT NULL,
                    whitelisted_channels BIGINT[] DEFAULT '{}',
                    state VARCHAR(20) DEFAULT 'active',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP
                );

                -- Phase 2: Stream D - フォーカスロック
                CREATE TABLE IF NOT EXISTS phone_lock_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    lock_type VARCHAR(20) NOT NULL,
                    duration_minutes INT NOT NULL,
                    coins_bet INT DEFAULT 0,
                    unlock_level INT DEFAULT 1,
                    state VARCHAR(20) DEFAULT 'active',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP
                );

                -- Phase 4: ロック設定
                CREATE TABLE IF NOT EXISTS user_lock_settings (
                    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                    default_unlock_level INT DEFAULT 1
                        CHECK (default_unlock_level BETWEEN 1 AND 5),
                    default_duration INT DEFAULT 60,
                    default_coin_bet INT DEFAULT 0,
                    block_categories TEXT[] DEFAULT '{}',
                    custom_blocked_urls TEXT[] DEFAULT '{}',
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );

                -- Phase 4: アンロックコード
                CREATE TABLE IF NOT EXISTS unlock_codes (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    session_id INT NOT NULL,
                    code VARCHAR(20) NOT NULL,
                    code_type VARCHAR(20) NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                -- Phase 4: コードリクエスト
                CREATE TABLE IF NOT EXISTS code_requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    session_id INT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                -- Phase 3: VCセッション
                CREATE TABLE IF NOT EXISTS vc_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL,
                    ended_at TIMESTAMPTZ,
                    duration_minutes INT,
                    auto_logged BOOLEAN DEFAULT TRUE
                );

                -- Phase 3: サーバー設定
                CREATE TABLE IF NOT EXISTS server_settings (
                    guild_id BIGINT PRIMARY KEY,
                    study_channels BIGINT[] DEFAULT '{}',
                    vc_channels BIGINT[] DEFAULT '{}',
                    admin_role_id BIGINT,
                    nudge_enabled BOOLEAN DEFAULT TRUE,
                    vc_tracking_enabled BOOLEAN DEFAULT TRUE,
                    min_vc_minutes INT DEFAULT 5,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );

                -- Phase 3: ユーザー設定
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                    display_name VARCHAR(100),
                    bio TEXT DEFAULT '',
                    timezone VARCHAR(50) DEFAULT 'Asia/Tokyo',
                    daily_goal_minutes INT DEFAULT 60,
                    notifications_enabled BOOLEAN DEFAULT TRUE,
                    theme VARCHAR(20) DEFAULT 'dark',
                    custom_title VARCHAR(100),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );

                -- Phase 2: Stream E - API認証
                CREATE TABLE IF NOT EXISTS api_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    token_hash VARCHAR(64) UNIQUE NOT NULL,
                    scopes TEXT[] DEFAULT '{}',
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    session_token VARCHAR(64) UNIQUE NOT NULL,
                    discord_access_token TEXT,
                    discord_refresh_token TEXT,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- デバイストークン
                CREATE TABLE IF NOT EXISTS device_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    device_token TEXT NOT NULL,
                    platform VARCHAR(10) NOT NULL
                        CHECK (platform IN ('ios', 'android', 'web')),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, device_token)
                );

                -- 通知ログ
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    type VARCHAR(50) NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT,
                    data JSONB,
                    sent_at TIMESTAMPTZ DEFAULT NOW(),
                    read_at TIMESTAMPTZ
                );

                -- Phase 5: コホートチャレンジ
                CREATE TABLE IF NOT EXISTS challenges (
                    id SERIAL PRIMARY KEY,
                    creator_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT DEFAULT '',
                    goal_type VARCHAR(30) DEFAULT 'study_minutes',
                    goal_target INT DEFAULT 0,
                    duration_days INT NOT NULL
                        CHECK (duration_days BETWEEN 3 AND 90),
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    channel_id BIGINT,
                    xp_multiplier FLOAT DEFAULT 1.5,
                    status VARCHAR(20) DEFAULT 'upcoming',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS challenge_participants (
                    id SERIAL PRIMARY KEY,
                    challenge_id INT NOT NULL
                        REFERENCES challenges(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    progress INT DEFAULT 0,
                    checkins INT DEFAULT 0,
                    last_checkin_date DATE,
                    completed BOOLEAN DEFAULT FALSE,
                    joined_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(challenge_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS challenge_checkins (
                    id SERIAL PRIMARY KEY,
                    challenge_id INT NOT NULL
                        REFERENCES challenges(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    checkin_date DATE NOT NULL,
                    progress_delta INT DEFAULT 0,
                    note TEXT DEFAULT '',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(challenge_id, user_id, checkin_date)
                );

                -- Phase 5: アクティビティイベント
                CREATE TABLE IF NOT EXISTS activity_events (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    event_data JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                -- Phase 5: バディマッチング
                CREATE TABLE IF NOT EXISTS buddy_profiles (
                    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                    subjects TEXT[] DEFAULT '{}',
                    preferred_times TEXT[] DEFAULT '{}',
                    study_style VARCHAR(30) DEFAULT 'focused',
                    active BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS buddy_matches (
                    id SERIAL PRIMARY KEY,
                    user_a BIGINT NOT NULL REFERENCES users(user_id),
                    user_b BIGINT NOT NULL REFERENCES users(user_id),
                    guild_id BIGINT NOT NULL,
                    subject VARCHAR(200),
                    compatibility_score FLOAT DEFAULT 0.0,
                    status VARCHAR(20) DEFAULT 'pending',
                    matched_at TIMESTAMPTZ DEFAULT NOW(),
                    ended_at TIMESTAMPTZ
                );

                CREATE TABLE IF NOT EXISTS buddy_sessions (
                    id SERIAL PRIMARY KEY,
                    match_id INT NOT NULL REFERENCES buddy_matches(id) ON DELETE CASCADE,
                    vc_channel_id BIGINT,
                    started_at TIMESTAMPTZ DEFAULT NOW(),
                    ended_at TIMESTAMPTZ,
                    total_minutes INT DEFAULT 0
                );

                -- Phase 5: AI週次インサイト
                CREATE TABLE IF NOT EXISTS weekly_reports (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    week_start DATE NOT NULL,
                    week_end DATE NOT NULL,
                    raw_data JSONB DEFAULT '{}',
                    insights JSONB DEFAULT '[]',
                    summary TEXT DEFAULT '',
                    generated_at TIMESTAMPTZ DEFAULT NOW(),
                    sent_via_dm BOOLEAN DEFAULT FALSE,
                    UNIQUE(user_id, week_start)
                );

                CREATE TABLE IF NOT EXISTS user_insights (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    insight_type VARCHAR(50) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    body TEXT NOT NULL,
                    data JSONB DEFAULT '{}',
                    confidence FLOAT DEFAULT 0.5,
                    active BOOLEAN DEFAULT TRUE,
                    generated_at TIMESTAMPTZ DEFAULT NOW()
                );

                -- Phase 5: クロスプラットフォームセッション
                CREATE TABLE IF NOT EXISTS active_cross_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    session_type VARCHAR(30) NOT NULL,
                    source_platform VARCHAR(10) NOT NULL,
                    session_ref_id INT,
                    topic VARCHAR(200) DEFAULT '',
                    duration_minutes INT NOT NULL,
                    started_at TIMESTAMPTZ DEFAULT NOW(),
                    end_time TIMESTAMPTZ NOT NULL,
                    state VARCHAR(20) DEFAULT 'active',
                    metadata JSONB DEFAULT '{}'
                );

                -- Phase 6: デイリークエスト
                CREATE TABLE IF NOT EXISTS daily_quests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    quest_type TEXT NOT NULL,
                    target INT NOT NULL,
                    progress INT DEFAULT 0,
                    reward_xp INT NOT NULL,
                    reward_coins INT NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    claimed BOOLEAN DEFAULT FALSE,
                    quest_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                -- Phase 6: スタディチーム
                CREATE TABLE IF NOT EXISTS study_teams (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    creator_id BIGINT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    max_members INT DEFAULT 10,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS team_members (
                    team_id INT NOT NULL REFERENCES study_teams(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    username TEXT NOT NULL,
                    joined_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (team_id, user_id)
                );

                -- ラーニングパス
                CREATE TABLE IF NOT EXISTS learning_paths (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    path_id TEXT NOT NULL,
                    current_milestone INT DEFAULT 0,
                    completed BOOLEAN DEFAULT FALSE,
                    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
                    completed_at TIMESTAMPTZ,
                    UNIQUE(user_id, path_id)
                );

                CREATE TABLE IF NOT EXISTS path_milestones (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    path_id TEXT NOT NULL,
                    milestone_index INT NOT NULL,
                    completed_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, path_id, milestone_index)
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

                -- Phase 2 indexes
                CREATE INDEX IF NOT EXISTS idx_virtual_currency_user
                    ON virtual_currency(user_id);
                CREATE INDEX IF NOT EXISTS idx_shop_items_category
                    ON shop_items(category, active);
                CREATE INDEX IF NOT EXISTS idx_user_inventory_user
                    ON user_inventory(user_id);
                CREATE INDEX IF NOT EXISTS idx_study_raids_guild
                    ON study_raids(guild_id, state);
                CREATE INDEX IF NOT EXISTS idx_raid_participants_raid
                    ON raid_participants(raid_id);
                CREATE INDEX IF NOT EXISTS idx_user_achievements_user
                    ON user_achievements(user_id);
                CREATE INDEX IF NOT EXISTS idx_flashcard_decks_user
                    ON flashcard_decks(user_id);
                CREATE INDEX IF NOT EXISTS idx_flashcards_deck
                    ON flashcards(deck_id, next_review);
                CREATE INDEX IF NOT EXISTS idx_study_plans_user
                    ON study_plans(user_id, status);
                CREATE INDEX IF NOT EXISTS idx_wellness_logs_user
                    ON wellness_logs(user_id, logged_at);
                CREATE INDEX IF NOT EXISTS idx_focus_sessions_user
                    ON focus_sessions(user_id, state);
                CREATE INDEX IF NOT EXISTS idx_phone_lock_user
                    ON phone_lock_sessions(user_id, state);
                CREATE INDEX IF NOT EXISTS idx_sessions_token
                    ON sessions(session_token);
                CREATE INDEX IF NOT EXISTS idx_device_tokens_user
                    ON device_tokens(user_id);
                CREATE INDEX IF NOT EXISTS idx_notification_logs_user
                    ON notification_logs(user_id, sent_at DESC);

                -- Phase 3 indexes
                CREATE INDEX IF NOT EXISTS idx_vc_sessions_user
                    ON vc_sessions(user_id, started_at);
                CREATE INDEX IF NOT EXISTS idx_vc_sessions_guild
                    ON vc_sessions(guild_id, started_at);

                -- Phase 4 indexes
                CREATE INDEX IF NOT EXISTS idx_unlock_codes_user
                    ON unlock_codes(user_id, used, expires_at);
                CREATE INDEX IF NOT EXISTS idx_code_requests_user
                    ON code_requests(user_id, status);

                -- Phase 5 indexes
                CREATE INDEX IF NOT EXISTS idx_activity_guild
                    ON activity_events(guild_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_buddy_matches_users
                    ON buddy_matches(user_a, user_b, status);
                CREATE INDEX IF NOT EXISTS idx_buddy_sessions_match
                    ON buddy_sessions(match_id);

                -- Phase 5: Challenge indexes
                CREATE INDEX IF NOT EXISTS idx_challenges_guild
                    ON challenges(guild_id, status);
                CREATE INDEX IF NOT EXISTS idx_challenge_participants
                    ON challenge_participants(challenge_id, user_id);
                CREATE INDEX IF NOT EXISTS idx_challenge_checkins
                    ON challenge_checkins(challenge_id, checkin_date);

                -- Phase 5: Insights indexes
                CREATE INDEX IF NOT EXISTS idx_weekly_reports_user
                    ON weekly_reports(user_id, week_start DESC);
                CREATE INDEX IF NOT EXISTS idx_user_insights
                    ON user_insights(user_id, active, generated_at DESC);

                -- Phase 5: Cross-platform session indexes
                CREATE INDEX IF NOT EXISTS idx_cross_sessions
                    ON active_cross_sessions(user_id, state) WHERE state = 'active';

                -- Phase 6: Daily quest indexes
                CREATE INDEX IF NOT EXISTS idx_daily_quests_user_date
                    ON daily_quests(user_id, quest_date);

                -- Phase 6: Study team indexes
                CREATE INDEX IF NOT EXISTS idx_study_teams_guild
                    ON study_teams(guild_id);
                CREATE INDEX IF NOT EXISTS idx_team_members_user
                    ON team_members(user_id);

                -- Learning path indexes
                CREATE INDEX IF NOT EXISTS idx_learning_paths_user
                    ON learning_paths(user_id, path_id);
                CREATE INDEX IF NOT EXISTS idx_path_milestones_user
                    ON path_milestones(user_id, path_id);

                -- Missing indexes
                CREATE INDEX IF NOT EXISTS idx_phone_nudges_user
                    ON phone_nudges(user_id);
                CREATE INDEX IF NOT EXISTS idx_nudge_history_user
                    ON nudge_history(user_id);
                CREATE INDEX IF NOT EXISTS idx_study_raids_creator
                    ON study_raids(creator_id);
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

            # デフォルト実績を挿入
            await conn.execute(  # noqa: E501
                """
                INSERT INTO achievements
                    (key, name, description, emoji,
                     category, target_value, reward_coins)
                VALUES
                    ('first_study', '初学者',
                     '初めて学習を記録した',
                     '📖', 'study', 1, 50),
                    ('study_100h', '100時間学習者',
                     '累計100時間学習した',
                     '📚', 'study', 6000, 500),
                    ('study_1000h', '1000時間学習者',
                     '累計1000時間学習した',
                     '🎓', 'study', 60000, 2000),
                    ('streak_7', '週間連続',
                     '7日連続で学習した',
                     '🔥', 'streak', 7, 100),
                    ('streak_30', '月間連続',
                     '30日連続で学習した',
                     '💪', 'streak', 30, 500),
                    ('first_raid', '初レイド',
                     '初めてスタディレイドに参加した',
                     '⚔️', 'raid', 1, 100),
                    ('raid_master', 'レイドマスター',
                     '10回スタディレイドを完了した',
                     '🛡️', 'raid', 10, 300),
                    ('task_50', 'タスクマスター',
                     '50件のタスクを完了した',
                     '✅', 'tasks', 50, 200)
                ON CONFLICT (key) DO NOTHING;
                """
            )

            # デフォルトショップアイテムを挿入
            await conn.execute(
                """
                INSERT INTO shop_items
                    (name, description, category,
                     price, rarity, emoji)
                VALUES
                    ('カスタムプロフィール題名',
                     'プロフィールの題名を変更できる',
                     'title', 100, 'common', '📝'),
                    ('ゴールドバッジ',
                     '金色のプロフィールバッジ',
                     'cosmetic', 200, 'rare', '🏅'),
                    ('XPブースト(1時間)',
                     '1時間XP獲得量1.5倍',
                     'boost', 150, 'uncommon', '⚡'),
                    ('XPブースト(24時間)',
                     '24時間XP獲得量1.5倍',
                     'boost', 500, 'rare', '⚡'),
                    ('レインボーバッジ',
                     '虹色のプロフィールバッジ',
                     'cosmetic', 1000, 'epic', '🌈'),
                    ('ダークテーマ',
                     'プロフィールをダークテーマに',
                     'theme', 300, 'uncommon', '🌙'),
                    ('ネオンテーマ',
                     'プロフィールをネオンテーマに',
                     'theme', 500, 'rare', '💫'),
                    ('ストリークシールド',
                     'ストリークリセット防止(1回)',
                     'boost', 800, 'epic', '🛡️'),
                    ('学習マスター ロール',
                     '特別な「学習マスター」ロールを取得',
                     'role', 500, 'epic', '👑'),
                    ('集中の達人 ロール',
                     '特別な「集中の達人」ロールを取得',
                     'role', 300, 'rare', '🎯'),
                    ('XPブースト 1.5x (24h)',
                     '24時間XP獲得量1.5倍ブースト',
                     'boost', 200, 'uncommon', '🚀'),
                    ('カスタム称号',
                     '自分だけのカスタム称号を設定',
                     'title', 150, 'uncommon', '🏷️'),
                    ('プロフィールテーマ: ゴールド',
                     'プロフィールをゴールドテーマに',
                     'theme', 100, 'common', '✨')
                ON CONFLICT DO NOTHING;
                """
            )

            logger.info("テーブル作成完了")

    async def close(self) -> None:
        """接続プールを閉じる"""
        if self.pool:
            await self.pool.close()
            logger.info("データベース接続を閉じました")
