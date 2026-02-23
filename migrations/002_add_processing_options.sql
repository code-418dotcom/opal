-- Add processing_options column to jobs table
-- Stores the AI pipeline flags (remove_background, generate_scene, upscale)
-- so they survive the gap between job creation and job enqueue.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS processing_options jsonb;
