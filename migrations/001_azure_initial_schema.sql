/*
  # OPAL Platform Initial Schema (Azure PostgreSQL)

  ## Overview
  Creates the core database schema for the OPAL AI Image Processing Platform on Azure PostgreSQL.

  ## Tables

  ### jobs
  Stores image processing job information.
  - `id` (text, primary key) - Unique job identifier
  - `tenant_id` (text, indexed) - Multi-tenant isolation
  - `brand_profile_id` (text) - Brand configuration reference
  - `correlation_id` (text, indexed) - Request tracing
  - `status` (enum) - Job status: created, processing, completed, failed, partial
  - `created_at` (timestamptz) - Creation timestamp
  - `updated_at` (timestamptz) - Last update timestamp

  ### job_items
  Stores individual items within a job.
  - `id` (text, primary key) - Unique item identifier
  - `job_id` (text, foreign key) - Parent job reference
  - `tenant_id` (text, indexed) - Multi-tenant isolation
  - `filename` (text) - Original filename
  - `status` (enum) - Item status: created, uploaded, processing, completed, failed
  - `raw_blob_path` (text, nullable) - Azure Blob Storage path for input
  - `output_blob_path` (text, nullable) - Azure Blob Storage path for output
  - `error_message` (text, nullable) - Error details if failed
  - `created_at` (timestamptz) - Creation timestamp
  - `updated_at` (timestamptz) - Last update timestamp

  ### job_queue
  Database-backed message queue for async processing (optional, Azure Service Bus recommended).
  - `id` (bigserial, primary key) - Queue message ID
  - `queue_name` (text) - Queue identifier (jobs, exports)
  - `payload` (jsonb) - Message data
  - `status` (enum) - Message status: pending, processing, completed, failed
  - `attempts` (integer) - Retry count
  - `max_attempts` (integer) - Maximum retries
  - `created_at` (timestamptz) - Creation timestamp
  - `processed_at` (timestamptz, nullable) - Processing timestamp
  - `error` (text, nullable) - Error details

  ## Indexes
  - Jobs: tenant_id, correlation_id, status
  - Job items: job_id, tenant_id, status
  - Queue: queue_name + status (for efficient polling)
*/

-- Create enums
DO $$ BEGIN
  CREATE TYPE job_status AS ENUM ('created', 'processing', 'completed', 'failed', 'partial');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE item_status AS ENUM ('created', 'uploaded', 'processing', 'completed', 'failed');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE queue_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
  id text PRIMARY KEY,
  tenant_id text NOT NULL,
  brand_profile_id text NOT NULL,
  correlation_id text NOT NULL,
  status job_status NOT NULL DEFAULT 'created',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Create indexes on jobs
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_id ON jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_jobs_correlation_id ON jobs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);

-- Create job_items table
CREATE TABLE IF NOT EXISTS job_items (
  id text PRIMARY KEY,
  job_id text NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  filename text NOT NULL,
  status item_status NOT NULL DEFAULT 'created',
  raw_blob_path text,
  output_blob_path text,
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Create indexes on job_items
CREATE INDEX IF NOT EXISTS idx_job_items_job_id ON job_items(job_id);
CREATE INDEX IF NOT EXISTS idx_job_items_tenant_id ON job_items(tenant_id);
CREATE INDEX IF NOT EXISTS idx_job_items_status ON job_items(status);

-- Create job_queue table
CREATE TABLE IF NOT EXISTS job_queue (
  id bigserial PRIMARY KEY,
  queue_name text NOT NULL,
  payload jsonb NOT NULL,
  status queue_status NOT NULL DEFAULT 'pending',
  attempts integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 3,
  created_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  error text
);

-- Create indexes on job_queue
CREATE INDEX IF NOT EXISTS idx_job_queue_status_queue ON job_queue(queue_name, status, created_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_job_queue_processing ON job_queue(status, processed_at) WHERE status = 'processing';

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS jobs_updated_at ON jobs;
CREATE TRIGGER jobs_updated_at
  BEFORE UPDATE ON jobs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS job_items_updated_at ON job_items;
CREATE TRIGGER job_items_updated_at
  BEFORE UPDATE ON job_items
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Brand profiles table (for future use)
CREATE TABLE IF NOT EXISTS brand_profiles (
  id text PRIMARY KEY,
  tenant_id text NOT NULL,
  name text NOT NULL,
  default_scene_prompt text,
  style_keywords text[],
  color_palette text[],
  mood text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brand_profiles_tenant_id ON brand_profiles(tenant_id);

-- Insert a default brand profile
INSERT INTO brand_profiles (id, tenant_id, name, default_scene_prompt, mood)
VALUES (
  'default_brand',
  'default_tenant',
  'Default Brand',
  'modern minimalist scene, bright natural lighting, clean background',
  'modern'
)
ON CONFLICT (id) DO NOTHING;
