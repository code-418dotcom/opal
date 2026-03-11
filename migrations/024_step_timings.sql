-- Migration 024: Add step timing data to job items
-- Tracks how long each pipeline phase takes (bg_removal, scene_edit, upscale, etc.)

ALTER TABLE job_items ADD COLUMN IF NOT EXISTS step_timings JSONB;
