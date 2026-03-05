-- Migration 011: Bootstrap admin user
-- Try email match (case-insensitive, also partial/contains match)
UPDATE users SET is_admin = true WHERE LOWER(email) = LOWER('info@aardvark-hosting.nl');
UPDATE users SET is_admin = true WHERE LOWER(email) LIKE '%aardvark%';
-- Fallback: make the first user admin unconditionally (early dev, single user)
UPDATE users SET is_admin = true
WHERE id = (SELECT id FROM users ORDER BY created_at ASC LIMIT 1);
