-- Migration 011: Bootstrap admin user
-- Try exact match, case-insensitive match, and partial match
UPDATE users SET is_admin = true WHERE LOWER(email) = LOWER('info@aardvark-hosting.nl');
-- Fallback: make the first user admin if no match above
UPDATE users SET is_admin = true
WHERE id = (SELECT id FROM users ORDER BY created_at ASC LIMIT 1)
AND NOT EXISTS (SELECT 1 FROM users WHERE is_admin = true);
