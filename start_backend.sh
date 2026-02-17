#!/bin/bash
# ⚠️ DO NOT COMMIT THIS FILE WITH REAL CREDENTIALS
# Copy this file to start_backend_local.sh and add to .gitignore

# Load from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Or set them manually here (for local development only):
# export DATABASE_URL=""
# export SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
# export SUPABASE_ANON_KEY="YOUR_ANON_KEY_HERE"
# export STORAGE_BACKEND="supabase"
# export QUEUE_BACKEND="database"
# export API_KEYS="dev_testkey123"

export PATH=$PATH:/home/appuser/.local/bin
export PYTHONDONTWRITEBYTECODE=1

cd /tmp/cc-agent/63778139/project
exec /home/appuser/.local/bin/uvicorn src.web_api.web_api.main:app --host 0.0.0.0 --port 8080
