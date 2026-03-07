-- Migration 013: Brand reference images for style extraction
-- Users upload example images, AI extracts style cues to enhance scene generation

CREATE TABLE IF NOT EXISTS brand_reference_images (
    id VARCHAR PRIMARY KEY,
    brand_profile_id VARCHAR NOT NULL REFERENCES brand_profiles(id) ON DELETE CASCADE,
    tenant_id VARCHAR NOT NULL,
    blob_path VARCHAR NOT NULL,
    extracted_style JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brand_ref_images_profile ON brand_reference_images(brand_profile_id);
