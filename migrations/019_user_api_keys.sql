-- Migration 019: User-generated API keys
-- Allows users to create named API keys for integrations (WooCommerce plugin, etc.)
-- Keys are stored as SHA-256 hashes; only the prefix is kept for display.

CREATE TABLE IF NOT EXISTS user_api_keys (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash        varchar(128) NOT NULL,   -- SHA-256 hex digest (never store plaintext)
    key_prefix      varchar(12)  NOT NULL,   -- first 8 chars for display ("opal_abc1...")
    name            varchar(100) NOT NULL DEFAULT '',  -- user label (e.g. "WooCommerce Store")
    created_at      timestamptz  NOT NULL DEFAULT now(),
    last_used_at    timestamptz,             -- updated on each authenticated request
    is_active       boolean      NOT NULL DEFAULT true
);

-- Fast lookup by hash during authentication
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_api_keys_hash
    ON user_api_keys(key_hash);

-- List keys belonging to a user
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user
    ON user_api_keys(user_id);

-- Auth path: lookup active key by hash in a single index scan
CREATE INDEX IF NOT EXISTS idx_user_api_keys_hash_active
    ON user_api_keys(key_hash, is_active);
