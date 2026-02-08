'''
Database migration: Add status field to jobs table

Run this script to update the database schema:
python scripts/migrate_add_job_status.py
'''
import os
import sys
from sqlalchemy import create_engine, text

# Add parent directory to path to import shared
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings

def migrate():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if status column exists
        result = conn.execute(text('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='jobs' AND column_name='status'
        '''))
        
        if result.fetchone():
            print('✅ Status column already exists')
            return
        
        print('Adding status column to jobs table...')
        
        # Add status column with default 'created'
        conn.execute(text('''
            ALTER TABLE jobs 
            ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'created'
        '''))
        
        # Create index on status
        conn.execute(text('''
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
        '''))
        
        conn.commit()
        
        print('✅ Migration completed successfully')

if __name__ == '__main__':
    migrate()
