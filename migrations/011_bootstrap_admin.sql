-- Migration 011: Bootstrap admin user
UPDATE users SET is_admin = true WHERE email = 'info@aardvark-hosting.nl';
