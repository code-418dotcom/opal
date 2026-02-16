#!/bin/bash
export DATABASE_URL=""
export SUPABASE_URL="https://jbwbdfabuffiwdphzzon.supabase.co"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impid2JkZmFidWZmaXdkcGh6em9uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEyMzI5ODgsImV4cCI6MjA4NjgwODk4OH0.UjUX0ft6k_E_H5twY8d3A1liMyKjgPpA1kAIDjU4__0"
export STORAGE_BACKEND="supabase"
export QUEUE_BACKEND="database"
export API_KEYS="dev_testkey123"
export PATH=$PATH:/home/appuser/.local/bin
export PYTHONDONTWRITEBYTECODE=1

cd /tmp/cc-agent/63778139/project
exec python3 -m uvicorn src.web_api.web_api.main:app --host 0.0.0.0 --port 8080
