/*
  # Fix Queue Processing Function

  ## Changes
  - Fix ambiguous column reference error in process_queue_messages function
  - Qualify column names with table alias to avoid ambiguity

  ## Details
  The previous version had "attempts = attempts + 1" which PostgreSQL couldn't resolve.
  Now using "attempts = jq.attempts + 1" to explicitly reference the table column.
*/

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
    attempts = jq.attempts + 1
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

GRANT EXECUTE ON FUNCTION process_queue_messages(text, integer) TO authenticated, service_role, anon;
