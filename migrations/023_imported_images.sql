-- Migration 023: Imported store images for re-use and re-processing
-- Stores original product images from connected stores in blob storage

CREATE TABLE IF NOT EXISTS imported_images (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id VARCHAR NOT NULL,
    integration_id VARCHAR NOT NULL REFERENCES integrations(id) ON DELETE CASCADE,
    provider_product_id VARCHAR NOT NULL,
    provider_image_id VARCHAR NOT NULL,
    blob_path VARCHAR NOT NULL,
    filename VARCHAR NOT NULL,
    original_url VARCHAR,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    content_type VARCHAR DEFAULT 'image/jpeg',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_imported_images_user ON imported_images(user_id);
CREATE INDEX IF NOT EXISTS idx_imported_images_integration ON imported_images(integration_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_imported_images_unique
    ON imported_images(integration_id, provider_product_id, provider_image_id);
