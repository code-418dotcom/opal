-- Migration 010: Admin settings + admin flag on users

-- Add is_admin flag to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin boolean NOT NULL DEFAULT false;

-- Admin settings table (key-value store with encryption for secrets)
CREATE TABLE IF NOT EXISTS admin_settings (
    key             text PRIMARY KEY,
    value           text NOT NULL,  -- encrypted if is_secret=true
    category        text NOT NULL DEFAULT 'general',
    is_secret       boolean NOT NULL DEFAULT false,
    description     text,
    updated_by      text REFERENCES users(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_settings_category ON admin_settings(category);

DROP TRIGGER IF EXISTS admin_settings_updated_at ON admin_settings;
CREATE TRIGGER admin_settings_updated_at
    BEFORE UPDATE ON admin_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Seed setting definitions (empty values — to be configured via admin UI)
-- These define what settings exist and their metadata; actual values come from env vars or admin UI
INSERT INTO admin_settings (key, value, category, is_secret, description) VALUES
    ('SHOPIFY_API_KEY',       '', 'shopify',     true,  'Shopify app API key (from Partner Dashboard)'),
    ('SHOPIFY_API_SECRET',    '', 'shopify',     true,  'Shopify app API secret'),
    ('SHOPIFY_SCOPES',        '', 'shopify',     false, 'OAuth scopes (comma-separated)'),
    ('MOLLIE_API_KEY',        '', 'payments',    true,  'Mollie API key for payment processing'),
    ('MOLLIE_WEBHOOK_SECRET', '', 'payments',    true,  'Mollie webhook verification secret'),
    ('FAL_API_KEY',           '', 'ai',          true,  'fal.ai API key for image generation'),
    ('REPLICATE_API_KEY',     '', 'ai',          true,  'Replicate API key (alternative image gen)'),
    ('ENCRYPTION_KEY',        '', 'security',    true,  'Fernet key for encrypting OAuth tokens at rest'),
    ('PUBLIC_BASE_URL',       '', 'general',     false, 'Public URL for webhooks and callbacks'),
    ('CORS_ALLOWED_ORIGINS',  '', 'general',     false, 'Allowed CORS origins (comma-separated)')
ON CONFLICT (key) DO NOTHING;
