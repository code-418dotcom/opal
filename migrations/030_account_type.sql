-- 030: Add account_type to users (consumer vs business)
ALTER TABLE users ADD COLUMN IF NOT EXISTS account_type VARCHAR(20) DEFAULT 'business';
