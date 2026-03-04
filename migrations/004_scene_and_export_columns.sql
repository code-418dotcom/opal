-- Migration 004: Add scene generation and export columns
-- Supports: custom scene prompts, multi-scene generation, export ZIP packaging

ALTER TABLE job_items ADD COLUMN IF NOT EXISTS scene_prompt text;
ALTER TABLE job_items ADD COLUMN IF NOT EXISTS scene_index integer;
ALTER TABLE job_items ADD COLUMN IF NOT EXISTS scene_type varchar(50);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS export_blob_path text;
