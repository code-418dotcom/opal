-- 021: Pixel tracking support for A/B tests
-- Adds pixel_key to integrations, variant log table, tracking_mode and auto_conclude to ab_tests

-- Pixel key for authenticating pixel events from storefronts
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS pixel_key VARCHAR(64);

-- Log of variant activations (start / swap) for attributing pixel events
CREATE TABLE IF NOT EXISTS ab_test_variant_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,
    variant VARCHAR(1) NOT NULL CHECK (variant IN ('a', 'b')),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (test_id, activated_at)
);
CREATE INDEX IF NOT EXISTS idx_variant_log_test_time ON ab_test_variant_log(test_id, activated_at);

-- Tracking mode: 'manual' (default, user enters metrics) or 'pixel' (automatic from storefront)
ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS tracking_mode VARCHAR(10) DEFAULT 'manual';

-- Whether to auto-conclude when significance is reached
ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS auto_conclude BOOLEAN DEFAULT FALSE;
