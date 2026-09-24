# -*- coding: utf-8 -*-
"""
Production PostgreSQL Database Connection and Connection Pool Manager.
- Robust SQLAlchemy 2.0 engine configuration with connection pooling
- Health checks, dead-connection auto-reconnect (pool_pre_ping), and query timeout safeguards
- Dynamic environment variable parsing with fallback support for 'analytics_platform' and 'datamind ai'
"""

import os
import urllib.parse
from typing import Generator, Dict, Any, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool

# Load environment configuration
load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "8210")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "analytics_platform")

# Retrieve or assemble DATABASE_URL safely
RAW_DATABASE_URL = os.getenv("DATABASE_URL")

if RAW_DATABASE_URL:
    DATABASE_URL = RAW_DATABASE_URL
else:
    # URL encode DB name if it contains spaces (e.g., 'datamind ai' -> 'datamind%20ai')
    encoded_dbname = urllib.parse.quote(DB_NAME)
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{encoded_dbname}"

# Pool parameters
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Initialize SQLAlchemy Engine with connection pool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # Test connections for liveness before checkout
    echo=False
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for Declarative ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Dict[str, Any]:
    """Health check diagnostic returning connection status and database engine stats."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version(), current_database(), current_user;")).fetchone()
            version_str = result[0] if result else "Unknown"
            db_name = result[1] if result else DB_NAME
            current_user = result[2] if result else DB_USER

            # Query count of major platform tables
            table_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            tables = [row[0] for row in conn.execute(table_query).fetchall()]

            pool_status = {
                "size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow()
            }

            return {
                "status": "healthy",
                "engine": "PostgreSQL",
                "version": version_str.split(" on ")[0] if " on " in version_str else version_str,
                "database": db_name,
                "user": current_user,
                "host": DB_HOST,
                "port": DB_PORT,
                "pool": pool_status,
                "tables_count": len(tables),
                "tables": tables
            }
    except Exception as exc:
        return {
            "status": "error",
            "engine": "PostgreSQL",
            "database": DB_NAME,
            "host": DB_HOST,
            "port": DB_PORT,
            "error": str(exc)
        }
