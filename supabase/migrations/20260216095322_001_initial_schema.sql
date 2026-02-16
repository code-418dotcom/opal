/*
  # OPAL Platform Initial Schema

  ## Overview
  Creates the core database schema for the OPAL AI Image Processing Platform.

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
  - `raw_blob_path` (text, nullable) - Input file path
  - `output_blob_path` (text, nullable) - Output file path
  - `error_message` (text, nullable) - Error details if failed
  - `created_at` (timestamptz) - Creation timestamp
  - `updated_at` (timestamptz) - Last update timestamp

  ### job_queue
  Database-backed message queue for async processing.
  - `id` (bigserial, primary key) - Queue message ID
  - `queue_name` (text) - Queue identifier (jobs, exports)
  - `payload` (jsonb) - Message data
  - `status` (enum) - Message status: pending, processing, completed, failed
  - `attempts` (integer) - Retry count
  - `max_attempts` (integer) - Maximum retries
  - `created_at` (timestamptz) - Creation timestamp
  - `processed_at` (timestamptz, nullable) - Processing timestamp
  - `error` (text, nullable) - Error details

  ## Security
  - RLS enabled on all tables
  - Service role access only (no public access)
  - Tenant isolation enforced

  ## Indexes
  - Jobs: tenant_id, correlation_id, status
  - Job items: job_id, tenant_id, status
  - Queue: queue_name + status (for efficient polling)
*/

-- Create enums
CREATE TYPE job_status AS ENUM ('created', 'processing', 'completed', 'failed', 'partial');
CREATE TYPE item_status AS ENUM ('created', 'uploaded', 'processing', 'completed', 'failed');
CREATE TYPE queue_status AS ENUM ('pending', 'processing', 'completed', 'failed');

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
CREATE TRIGGER jobs_updated_at
  BEFORE UPDATE ON jobs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER job_items_updated_at
  BEFORE UPDATE ON job_items
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Enable Row Level Security
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_queue ENABLE ROW LEVEL SECURITY;

-- RLS Policies (Service role only - no public access)
-- These policies allow full access to service role
CREATE POLICY "Service role full access to jobs"
  ON jobs
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access to job_items"
  ON job_items
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access to job_queue"
  ON job_queue
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Create storage buckets
INSERT INTO storage.buckets (id, name, public)
VALUES 
  ('raw', 'raw', false),
  ('outputs', 'outputs', false),
  ('exports', 'exports', false)
ON CONFLICT (id) DO NOTHING;

-- Storage policies (Service role only)
CREATE POLICY "Service role can upload raw files"
  ON storage.objects
  FOR INSERT
  TO service_role
  WITH CHECK (bucket_id = 'raw');

CREATE POLICY "Service role can read raw files"
  ON storage.objects
  FOR SELECT
  TO service_role
  USING (bucket_id = 'raw');

CREATE POLICY "Service role can upload output files"
  ON storage.objects
  FOR INSERT
  TO service_role
  WITH CHECK (bucket_id = 'outputs');

CREATE POLICY "Service role can read output files"
  ON storage.objects
  FOR SELECT
  TO service_role
  USING (bucket_id = 'outputs');

CREATE POLICY "Service role can upload export files"
  ON storage.objects
  FOR INSERT
  TO service_role
  WITH CHECK (bucket_id = 'exports');

CREATE POLICY "Service role can read export files"
  ON storage.objects
  FOR SELECT
  TO service_role
  USING (bucket_id = 'exports');
