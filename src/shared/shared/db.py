from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

# Only create SQLAlchemy engine if DATABASE_URL is provided
# When using Supabase, the Supabase client handles all database interactions
if settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=10,
        pool_recycle=3600,
        connect_args={
            "connect_timeout": 10,
            "application_name": "opal"
        }
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
else:
    engine = None
    SessionLocal = None


class Base(DeclarativeBase):
    pass
