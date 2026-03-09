-- Migration 018: Revised pricing tiers
-- One-time packs: Starter (25/€4.90), Growth (100/€14.90), Pro (500/€49.90), Bulk (2000/€149.90)
-- Subscriptions: Hobby (25/€3.90), Shop (100/€12.90), Business (500/€49.90), Agency (2000/€149.90)

-- Deactivate old one-time packages
UPDATE token_packages SET active = false WHERE id IN ('pkg_starter', 'pkg_pro', 'pkg_business');

-- Insert new one-time packages
INSERT INTO token_packages (id, name, tokens, price_cents, currency, active) VALUES
    ('pkg_starter_v2',  'Starter',  25,   490,   'EUR', true),
    ('pkg_growth',      'Growth',   100,  1490,  'EUR', true),
    ('pkg_pro_v2',      'Pro',      500,  4990,  'EUR', true),
    ('pkg_bulk',        'Bulk',     2000, 14990, 'EUR', true)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    tokens = EXCLUDED.tokens,
    price_cents = EXCLUDED.price_cents,
    active = EXCLUDED.active;

-- Deactivate old subscription plans
UPDATE subscription_plans SET active = false WHERE id IN ('plan_starter', 'plan_pro', 'plan_business');

-- Insert new subscription plans
INSERT INTO subscription_plans (id, name, tokens_per_month, price_cents, currency, interval, active) VALUES
    ('plan_hobby',       'Hobby',    25,   390,   'EUR', '1 month', true),
    ('plan_shop',        'Shop',     100,  1290,  'EUR', '1 month', true),
    ('plan_business_v2', 'Business', 500,  4990,  'EUR', '1 month', true),
    ('plan_agency',      'Agency',   2000, 14990, 'EUR', '1 month', true)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    tokens_per_month = EXCLUDED.tokens_per_month,
    price_cents = EXCLUDED.price_cents,
    active = EXCLUDED.active;
