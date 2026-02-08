-- =============================================================
-- StudyBot Phase 5: Realtime & Social Features Migration
-- Date: 2026-02-08
-- Description:
--   Adds tables and indexes for Phase 5 features:
--     - Activity event stream (real-time activity tracking)
--     - Buddy matching system (study partner pairing)
--     - Cohort challenges (group study challenges)
--     - AI weekly insights & reports
--     - Cross-platform session management
-- =============================================================

BEGIN;

-- ---------------------------------------------------------
-- Phase 5: Activity Events (real-time activity stream)
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS activity_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    guild_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------
-- Phase 5: Buddy Matching System
-- ---------------------------------------------------------

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
    match_id INT NOT NULL REFERENCES buddy_matches(id),
    vc_channel_id BIGINT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    total_minutes INT DEFAULT 0
);

-- ---------------------------------------------------------
-- Phase 5: Cohort Challenges
-- ---------------------------------------------------------

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

-- ---------------------------------------------------------
-- Phase 5: AI Weekly Insights & Reports
-- ---------------------------------------------------------

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

-- ---------------------------------------------------------
-- Phase 5: Cross-Platform Session Management
-- ---------------------------------------------------------

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

-- ---------------------------------------------------------
-- Phase 5: Indexes
-- ---------------------------------------------------------

-- Activity events
CREATE INDEX IF NOT EXISTS idx_activity_guild
    ON activity_events(guild_id, created_at DESC);

-- Buddy matching
CREATE INDEX IF NOT EXISTS idx_buddy_matches_users
    ON buddy_matches(user_a, user_b, status);
CREATE INDEX IF NOT EXISTS idx_buddy_sessions_match
    ON buddy_sessions(match_id);

-- Challenges
CREATE INDEX IF NOT EXISTS idx_challenges_guild
    ON challenges(guild_id, status);
CREATE INDEX IF NOT EXISTS idx_challenge_participants
    ON challenge_participants(challenge_id, user_id);
CREATE INDEX IF NOT EXISTS idx_challenge_checkins
    ON challenge_checkins(challenge_id, checkin_date);

-- Insights
CREATE INDEX IF NOT EXISTS idx_weekly_reports_user
    ON weekly_reports(user_id, week_start DESC);
CREATE INDEX IF NOT EXISTS idx_user_insights
    ON user_insights(user_id, active, generated_at DESC);

-- Cross-platform sessions (partial index for active sessions only)
CREATE INDEX IF NOT EXISTS idx_cross_sessions
    ON active_cross_sessions(user_id, state) WHERE state = 'active';

COMMIT;
