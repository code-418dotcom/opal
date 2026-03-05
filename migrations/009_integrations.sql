-- Migration 009: Integrations (generic provider support + cost config)

-- Integration provider enum
DO $$ BEGIN
  CREATE TYPE integration_provider AS ENUM ('shopify', 'woocommerce', 'etsy');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Integration status
DO $$ BEGIN
  CREATE TYPE integration_status AS ENUM ('active', 'disconnected', 'expired');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Integrations table (one per user+provider+store)
CREATE TABLE IF NOT EXISTS integrations (
    id                      text PRIMARY KEY,
    user_id                 text NOT NULL REFERENCES users(id),
    tenant_id               text NOT NULL,
    provider                integration_provider NOT NULL,
    store_url               text NOT NULL,
    access_token_encrypted  text NOT NULL,
    scopes                  text,
    status                  integration_status NOT NULL DEFAULT 'active',
    provider_metadata       jsonb,  -- provider-specific data (e.g. shopify shop info)
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_integrations_user ON integrations(user_id);
CREATE INDEX IF NOT EXISTS idx_integrations_tenant ON integrations(tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_integrations_user_provider_store
    ON integrations(user_id, provider, store_url);

DROP TRIGGER IF EXISTS integrations_updated_at ON integrations;
CREATE TRIGGER integrations_updated_at
    BEFORE UPDATE ON integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Configurable token costs per integration action
CREATE TABLE IF NOT EXISTS integration_costs (
    id          text PRIMARY KEY,
    provider    integration_provider NOT NULL,
    action      text NOT NULL,  -- e.g. 'process_image', 'push_back'
    token_cost  integer NOT NULL DEFAULT 1,
    active      boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_integration_costs_provider_action
    ON integration_costs(provider, action);

-- Seed default costs
INSERT INTO integration_costs (id, provider, action, token_cost, active) VALUES
    ('ic_shopify_process',  'shopify',     'process_image', 1, true),
    ('ic_shopify_pushback', 'shopify',     'push_back',     0, true),
    ('ic_woo_process',      'woocommerce', 'process_image', 1, true),
    ('ic_woo_pushback',     'woocommerce', 'push_back',     0, true),
    ('ic_etsy_process',     'etsy',        'process_image', 1, true),
    ('ic_etsy_pushback',    'etsy',        'push_back',     0, true)
ON CONFLICT (id) DO NOTHING;
