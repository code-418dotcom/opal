#!/bin/bash
set -e

echo "========================================"
echo "OPAL Azure PostgreSQL Setup"
echo "========================================"
echo ""

# Configuration
DB_HOST="opal-dev-dbeia4dlnxsy4-pg-ne.postgres.database.azure.com"
DB_NAME="opal"
DB_USER="opaladmin"
DB_PORT="5432"

# Check if psql is installed
command -v psql >/dev/null 2>&1 || {
  echo "Error: psql not installed. Install PostgreSQL client:"
  echo "  Ubuntu/Debian: sudo apt-get install postgresql-client"
  echo "  macOS: brew install postgresql"
  echo "  Windows: Download from https://www.postgresql.org/download/"
  exit 1
}

# Prompt for password if not set
if [ -z "$PGPASSWORD" ]; then
  echo "Enter database password for user $DB_USER:"
  read -s PGPASSWORD
  export PGPASSWORD
  echo ""
fi

echo "Testing connection to Azure PostgreSQL..."
if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT -c "SELECT version();" >/dev/null 2>&1; then
  echo "Error: Could not connect to database"
  echo "Check your credentials and network connection"
  exit 1
fi

echo "✓ Connected successfully"
echo ""

echo "Running migration: 001_azure_initial_schema.sql"
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT -f migrations/001_azure_initial_schema.sql

echo ""
echo "========================================"
echo "✓ Database Setup Complete!"
echo "========================================"
echo ""
echo "Tables created:"
echo "  - jobs"
echo "  - job_items"
echo "  - job_queue"
echo "  - brand_profiles"
echo ""
echo "Verify setup:"
echo "  psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT -c '\\dt'"
echo ""
