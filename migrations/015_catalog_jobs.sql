-- Migration 015: Catalog jobs for bulk processing
-- A catalog_job tracks bulk processing of an entire store's product catalog

CREATE TABLE IF NOT EXISTS catalog_jobs (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    integration_id VARCHAR NOT NULL REFERENCES integrations(id) ON DELETE CASCADE,
    status VARCHAR NOT NULL DEFAULT 'created',  -- created, processing, completed, failed, canceled
    total_products INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    total_images INTEGER NOT NULL DEFAULT 0,
    tokens_estimated INTEGER NOT NULL DEFAULT 0,
    tokens_spent INTEGER NOT NULL DEFAULT 0,
    settings JSONB DEFAULT '{}',  -- processing_options, brand_profile_id, auto_push_back, etc.
    error_message VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_catalog_jobs_user ON catalog_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_catalog_jobs_status ON catalog_jobs(status);

-- Links individual pipeline jobs to the parent catalog job
CREATE TABLE IF NOT EXISTS catalog_job_products (
    id VARCHAR PRIMARY KEY,
    catalog_job_id VARCHAR NOT NULL REFERENCES catalog_jobs(id) ON DELETE CASCADE,
    product_id VARCHAR NOT NULL,           -- external product ID (Shopify/Etsy/WooCommerce)
    product_title VARCHAR,
    job_id VARCHAR REFERENCES jobs(id),    -- the pipeline job processing this product's images
    image_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed, skipped
    error_message VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_catalog_job_products_catalog ON catalog_job_products(catalog_job_id);
CREATE INDEX IF NOT EXISTS idx_catalog_job_products_job ON catalog_job_products(job_id);
