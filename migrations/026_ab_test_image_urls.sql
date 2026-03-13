-- Migration 026: Add image URL support for A/B tests
-- Allows tests to be created with direct image URLs (from Shopify CDN etc.)
-- instead of requiring Opal job_item_ids.

ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS variant_a_image_url TEXT;
ALTER TABLE ab_tests ADD COLUMN IF NOT EXISTS variant_b_image_url TEXT;
