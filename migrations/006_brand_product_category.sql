-- Migration 006: Add product_category to brand_profiles
ALTER TABLE brand_profiles ADD COLUMN IF NOT EXISTS product_category varchar(100);
