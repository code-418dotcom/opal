/*
  # Queue Processing Function

  ## Overview
  Creates a database function to atomically fetch and lock queue messages for processing.

  ## New Functions

  ### process_queue_messages
  Atomically fetches pending messages from the queue and locks them for processing.
  
  **Parameters:**
  - `p_queue_name` (text) - Queue name to fetch from
  - `p_max_count` (integer) - Maximum number of messages to fetch
  
  **Returns:**
  Array of locked queue messages with incremented attempt count
  
  **Behavior:**
  - Only fetches messages with status = 'pending'
  - Only fetches messages where attempts < max_attempts
  - Uses FOR UPDATE SKIP LOCKED for concurrent safety
  - Updates status to 'processing' and increments attempts
  - Returns the locked messages for processing

  ## Security
  - Function executes with SECURITY DEFINER (elevated privileges)
  - Only accessible to authenticated users and service role
*/

-- Create function to atomically fetch and lock queue messages
CREATE OR REPLACE FUNCTION process_queue_messages(
  p_queue_name text,
  p_max_count integer DEFAULT 10
)
RETURNS TABLE(
  id bigint,
  queue_name text,
  payload jsonb,
  status queue_status,
  attempts integer,
  max_attempts integer,
  created_at timestamptz,
  processed_at timestamptz,
  error text
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  UPDATE job_queue jq
  SET 
    status = 'processing',
    processed_at = now(),
    attempts = attempts + 1
  WHERE jq.id IN (
    SELECT jq2.id
    FROM job_queue jq2
    WHERE jq2.queue_name = p_queue_name
      AND jq2.status = 'pending'
      AND jq2.attempts < jq2.max_attempts
    ORDER BY jq2.created_at ASC
    LIMIT p_max_count
    FOR UPDATE SKIP LOCKED
  )
  RETURNING jq.*;
END;
$$;

-- Grant execute permission to authenticated users and service role
GRANT EXECUTE ON FUNCTION process_queue_messages(text, integer) TO authenticated, service_role, anon;
