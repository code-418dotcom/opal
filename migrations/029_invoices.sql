-- 029: Invoices and VAT tracking on payments

-- Add VAT fields to payments
ALTER TABLE payments ADD COLUMN IF NOT EXISTS amount_net_cents INTEGER;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS vat_rate NUMERIC(5,2) DEFAULT 0;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS vat_amount_cents INTEGER DEFAULT 0;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS buyer_vat_number VARCHAR(50);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS vat_reverse_charged BOOLEAN DEFAULT FALSE;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS vat_exempt_reason VARCHAR(100);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR PRIMARY KEY,
    invoice_number VARCHAR(30) NOT NULL UNIQUE,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payment_id VARCHAR NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    -- Amounts (all in cents)
    amount_net_cents INTEGER NOT NULL,
    vat_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
    vat_amount_cents INTEGER NOT NULL DEFAULT 0,
    amount_total_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    -- VAT details
    vat_reverse_charged BOOLEAN NOT NULL DEFAULT FALSE,
    vat_exempt_reason VARCHAR(100),
    -- Buyer snapshot (captured at invoice time)
    buyer_name VARCHAR(200),
    buyer_company VARCHAR(200),
    buyer_vat_number VARCHAR(50),
    buyer_address_line1 VARCHAR(200),
    buyer_address_line2 VARCHAR(200),
    buyer_city VARCHAR(100),
    buyer_postal_code VARCHAR(20),
    buyer_country VARCHAR(2),
    buyer_email VARCHAR(200),
    -- Description
    description VARCHAR(500),
    -- PDF storage
    pdf_blob_path VARCHAR(500),
    -- Timestamps
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_payment_id ON invoices(payment_id);

-- Sequential invoice number counter
CREATE SEQUENCE IF NOT EXISTS invoice_number_seq START 1;
