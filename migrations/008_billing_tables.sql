-- Migration 008: Token billing tables

-- Token transaction types
DO $$ BEGIN
  CREATE TYPE token_tx_type AS ENUM ('purchase', 'usage', 'refund', 'bonus');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Payment status
DO $$ BEGIN
  CREATE TYPE payment_status AS ENUM ('pending', 'paid', 'failed', 'expired', 'refunded');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Token transaction ledger
CREATE TABLE IF NOT EXISTS token_transactions (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES users(id),
    amount          integer NOT NULL,  -- positive = credit, negative = debit
    type            token_tx_type NOT NULL,
    description     text,
    reference_id    text,  -- mollie payment ID, job_id, etc.
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_token_tx_user ON token_transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_token_tx_ref ON token_transactions(reference_id) WHERE reference_id IS NOT NULL;

-- Purchasable token packages
CREATE TABLE IF NOT EXISTS token_packages (
    id              text PRIMARY KEY,
    name            text NOT NULL,
    tokens          integer NOT NULL,
    price_cents     integer NOT NULL,
    currency        text NOT NULL DEFAULT 'EUR',
    active          boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Seed initial packages
INSERT INTO token_packages (id, name, tokens, price_cents, currency, active) VALUES
    ('pkg_starter',  'Starter',  50,  990,  'EUR', true),
    ('pkg_pro',      'Pro',      200, 2990, 'EUR', true),
    ('pkg_business', 'Business', 500, 5990, 'EUR', true)
ON CONFLICT (id) DO NOTHING;

-- Payment records (Mollie)
CREATE TABLE IF NOT EXISTS payments (
    id                  text PRIMARY KEY,
    user_id             text NOT NULL REFERENCES users(id),
    package_id          text NOT NULL REFERENCES token_packages(id),
    mollie_payment_id   text UNIQUE,
    amount_cents        integer NOT NULL,
    currency            text NOT NULL DEFAULT 'EUR',
    status              payment_status NOT NULL DEFAULT 'pending',
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_mollie ON payments(mollie_payment_id) WHERE mollie_payment_id IS NOT NULL;

DROP TRIGGER IF EXISTS payments_updated_at ON payments;
CREATE TRIGGER payments_updated_at
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
