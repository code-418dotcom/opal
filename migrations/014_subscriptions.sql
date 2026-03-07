-- Migration 014: Recurring subscription support via Mollie
-- Subscription plans define monthly token refreshes

CREATE TABLE IF NOT EXISTS subscription_plans (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    tokens_per_month INTEGER NOT NULL,
    price_cents INTEGER NOT NULL,
    currency VARCHAR NOT NULL DEFAULT 'EUR',
    interval VARCHAR NOT NULL DEFAULT '1 month',  -- Mollie interval format
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed default subscription plans
INSERT INTO subscription_plans (id, name, tokens_per_month, price_cents, currency, interval, active) VALUES
    ('plan_starter', 'Starter', 50, 2900, 'EUR', '1 month', true),
    ('plan_pro', 'Pro', 200, 8900, 'EUR', '1 month', true),
    ('plan_business', 'Business', 1000, 24900, 'EUR', '1 month', true)
ON CONFLICT (id) DO NOTHING;

-- Track user subscriptions
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    plan_id VARCHAR NOT NULL REFERENCES subscription_plans(id),
    mollie_customer_id VARCHAR,
    mollie_subscription_id VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'pending',  -- pending, active, canceled, expired
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_mollie ON user_subscriptions(mollie_subscription_id);

-- Store Mollie customer ID on users for recurring payments
ALTER TABLE users ADD COLUMN IF NOT EXISTS mollie_customer_id VARCHAR;
