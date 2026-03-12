-- Migration 025: Pixel tracking for automatic A/B test metric collection
-- Adds pixel key auth for storefront event ingestion and variant swap history.

-- Pixel key on integrations: allows storefront pixel to authenticate without user JWT
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS pixel_key VARCHAR(64);
CREATE UNIQUE INDEX IF NOT EXISTS idx_integrations_pixel_key ON integrations(pixel_key) WHERE pixel_key IS NOT NULL;

-- Variant activation log: records every start/swap so we can attribute events
-- to the correct variant by timestamp.
CREATE TABLE IF NOT EXISTS ab_test_variant_log (
    id VARCHAR PRIMARY KEY,
    test_id VARCHAR NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,
    variant VARCHAR(1) NOT NULL,  -- 'a' or 'b'
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (test_id, activated_at)
);
CREATE INDEX IF NOT EXISTS idx_variant_log_test ON ab_test_variant_log(test_id, activated_at);

-- Tracking mode on ab_tests: distinguish manual entry from automatic pixel tracking
ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS tracking_mode VARCHAR NOT NULL DEFAULT 'manual';
-- Values: 'manual' (existing behavior) or 'pixel' (automatic via web pixel)
