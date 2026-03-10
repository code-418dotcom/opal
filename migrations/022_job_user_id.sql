-- Migration 022: Add user_id to jobs table
-- Links jobs to the user who created them for reliable token refunds

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS user_id VARCHAR REFERENCES users(id);

CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id) WHERE user_id IS NOT NULL;
