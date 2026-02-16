/*
  # Storage Bucket Policies

  1. Changes
    - Enable RLS policies for storage buckets
    - Allow authenticated and anon users to upload/download files
    - Policies are permissive for development

  2. Security Notes
    - These policies allow full access for development
    - In production, add proper user/tenant isolation
*/

-- Allow all operations on raw bucket for development
CREATE POLICY "Allow all operations on raw bucket"
  ON storage.objects
  FOR ALL
  TO anon, authenticated
  USING (bucket_id = 'raw')
  WITH CHECK (bucket_id = 'raw');

-- Allow all operations on outputs bucket for development
CREATE POLICY "Allow all operations on outputs bucket"
  ON storage.objects
  FOR ALL
  TO anon, authenticated
  USING (bucket_id = 'outputs')
  WITH CHECK (bucket_id = 'outputs');

-- Allow all operations on exports bucket for development
CREATE POLICY "Allow all operations on exports bucket"
  ON storage.objects
  FOR ALL
  TO anon, authenticated
  USING (bucket_id = 'exports')
  WITH CHECK (bucket_id = 'exports');
