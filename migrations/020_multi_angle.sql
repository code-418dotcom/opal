-- Migration 020: Multi-angle product photography
-- Adds angle_type to job_items for generating different product views

ALTER TABLE job_items ADD COLUMN IF NOT EXISTS angle_type VARCHAR(50);

-- Index for filtering by angle type
CREATE INDEX IF NOT EXISTS idx_job_items_angle_type ON job_items(angle_type) WHERE angle_type IS NOT NULL;
