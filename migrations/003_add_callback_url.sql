-- Add callback_url column to jobs table for webhook notifications
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS callback_url text;
