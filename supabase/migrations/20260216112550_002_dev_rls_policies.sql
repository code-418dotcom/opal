/*
  # Add Development RLS Policies

  1. Changes
    - Add RLS policies that allow anon key access for development
    - These policies allow full access for development purposes
    - In production, these should be replaced with proper authentication-based policies

  2. Security Notes
    - These policies are permissive for local development
    - Production should use proper user authentication and tenant isolation
*/

-- Drop existing restrictive policies
DROP POLICY IF EXISTS "Service role full access to jobs" ON jobs;
DROP POLICY IF EXISTS "Service role full access to job_items" ON job_items;

-- Jobs table policies (development - allow all operations)
CREATE POLICY "Allow all operations on jobs for development"
  ON jobs
  FOR ALL
  TO anon, authenticated
  USING (true)
  WITH CHECK (true);

-- Job items table policies (development - allow all operations)
CREATE POLICY "Allow all operations on job_items for development"
  ON job_items
  FOR ALL
  TO anon, authenticated
  USING (true)
  WITH CHECK (true);
