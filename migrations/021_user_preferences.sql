-- Migration 021: User preferences for UX settings
-- Stores per-user UI preferences (help tooltips, tips bar, etc.)

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE PRIMARY KEY,
    preferences JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
