-- Migration 012: Add SEO metadata columns to job_items
-- Stores AI-generated alt-text and SEO-optimized filenames

ALTER TABLE job_items ADD COLUMN IF NOT EXISTS seo_alt_text VARCHAR(200);
ALTER TABLE job_items ADD COLUMN IF NOT EXISTS seo_filename VARCHAR(255);
