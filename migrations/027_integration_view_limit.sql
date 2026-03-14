-- Add monthly view limit to integrations.
-- NULL = unlimited (paid plans), 1000 = free tier default.
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS monthly_event_limit INT DEFAULT 1000;
