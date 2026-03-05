-- Migration 007: Users table for Entra External ID auth
-- Supports JIT provisioning (user created on first login)

CREATE TABLE IF NOT EXISTS users (
    id                  text PRIMARY KEY,
    entra_subject_id    text UNIQUE,
    email               text NOT NULL,
    tenant_id           text NOT NULL,
    display_name        text,
    token_balance       integer NOT NULL DEFAULT 0,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_entra_subject
    ON users(entra_subject_id) WHERE entra_subject_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
