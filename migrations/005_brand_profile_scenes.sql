-- Migration 005: Brand profile scene defaults + scene templates + saved background support
-- Depends on: 004_scene_and_export_columns.sql

-- Extend brand_profiles with scene defaults
ALTER TABLE brand_profiles ADD COLUMN IF NOT EXISTS default_scene_count integer DEFAULT 1;
ALTER TABLE brand_profiles ADD COLUMN IF NOT EXISTS default_scene_types text[];

-- Scene templates table
CREATE TABLE IF NOT EXISTS scene_templates (
    id               text PRIMARY KEY,
    tenant_id        text NOT NULL,
    brand_profile_id text REFERENCES brand_profiles(id) ON DELETE SET NULL,
    name             varchar(255) NOT NULL,
    prompt           text NOT NULL,
    preview_blob_path text,
    scene_type       varchar(50),
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scene_templates_tenant ON scene_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_scene_templates_brand ON scene_templates(brand_profile_id);

-- Support "use exact background" on job items
ALTER TABLE job_items ADD COLUMN IF NOT EXISTS saved_background_path text;
