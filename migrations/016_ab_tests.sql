-- Migration 016: A/B image testing
-- Track image variant experiments and their performance metrics

CREATE TABLE IF NOT EXISTS ab_tests (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    integration_id VARCHAR NOT NULL REFERENCES integrations(id) ON DELETE CASCADE,
    product_id VARCHAR NOT NULL,           -- external product ID
    product_title VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'created',  -- created, running, concluded, canceled
    variant_a_job_item_id VARCHAR REFERENCES job_items(id),
    variant_b_job_item_id VARCHAR REFERENCES job_items(id),
    variant_a_label VARCHAR DEFAULT 'Original',
    variant_b_label VARCHAR DEFAULT 'Variant B',
    active_variant VARCHAR NOT NULL DEFAULT 'a',  -- which variant is currently live: 'a' or 'b'
    winner VARCHAR,                         -- 'a', 'b', or null if not concluded
    original_image_id VARCHAR,              -- store's original image ID (for restoration)
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ab_tests_user ON ab_tests(user_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON ab_tests(status);
CREATE INDEX IF NOT EXISTS idx_ab_tests_integration ON ab_tests(integration_id);

CREATE TABLE IF NOT EXISTS ab_test_metrics (
    id VARCHAR PRIMARY KEY,
    ab_test_id VARCHAR NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,
    variant VARCHAR NOT NULL,              -- 'a' or 'b'
    date DATE NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    add_to_carts INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    revenue_cents INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE(ab_test_id, variant, date)
);

CREATE INDEX IF NOT EXISTS idx_ab_test_metrics_test ON ab_test_metrics(ab_test_id);
