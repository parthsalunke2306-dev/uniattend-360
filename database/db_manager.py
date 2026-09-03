"""
Database Connection Manager and Session Factory for UniAttend Analytics.
Handles database initialization, engine management, session pooling, and utility helpers.
"""

import os
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

# Automatically load .env file if present
load_dotenv()

# Default SQLite database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "uniattend.db")
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_PATH}"

# Connection string can be overridden by environment variable for PostgreSQL / Supabase / Neon
DATABASE_URL = os.environ.get("UNIATTEND_DATABASE_URL", DEFAULT_DB_URL)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure engine with production connection pooling
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
        pool_pre_ping=True
    )
else:
    # Production PostgreSQL / Supabase pool configuration
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=300
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all database tables defined in the metadata and migrate missing columns."""
    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "user_accounts" in inspector.get_table_names():
            existing_cols = {c["name"] for c in inspector.get_columns("user_accounts")}
            with engine.begin() as conn:
                bool_default = "FALSE"
                if "must_change_password" not in existing_cols:
                    conn.execute(text(f"ALTER TABLE user_accounts ADD COLUMN must_change_password BOOLEAN DEFAULT {bool_default}"))
                if "is_device_bound" not in existing_cols:
                    conn.execute(text(f"ALTER TABLE user_accounts ADD COLUMN is_device_bound BOOLEAN DEFAULT {bool_default}"))
                if "bound_device_name" not in existing_cols:
                    conn.execute(text("ALTER TABLE user_accounts ADD COLUMN bound_device_name VARCHAR(150)"))
                if "bound_device_uuid" not in existing_cols:
                    conn.execute(text("ALTER TABLE user_accounts ADD COLUMN bound_device_uuid VARCHAR(150)"))
                if "device_reset_status" not in existing_cols:
                    conn.execute(text("ALTER TABLE user_accounts ADD COLUMN device_reset_status VARCHAR(20) DEFAULT 'NONE'"))
        if "silver_fact_attendance" in inspector.get_table_names():
            sfa_cols = {c["name"] for c in inspector.get_columns("silver_fact_attendance")}
            with engine.begin() as conn:
                if "user_id" not in sfa_cols:
                    conn.execute(text("ALTER TABLE silver_fact_attendance ADD COLUMN user_id INTEGER REFERENCES user_accounts(id) ON DELETE CASCADE"))
                if "lecture_session_id" not in sfa_cols:
                    conn.execute(text("ALTER TABLE silver_fact_attendance ADD COLUMN lecture_session_id VARCHAR(100) REFERENCES lecture_sessions(id) ON DELETE SET NULL"))
                if "biometrically_verified" not in sfa_cols:
                    conn.execute(text("ALTER TABLE silver_fact_attendance ADD COLUMN biometrically_verified BOOLEAN DEFAULT FALSE NOT NULL"))
                if "passkey_id" not in sfa_cols:
                    conn.execute(text("ALTER TABLE silver_fact_attendance ADD COLUMN passkey_id INTEGER REFERENCES passkeys(id) ON DELETE SET NULL"))
    except Exception as e:
        print(f"[DB MIGRATION] Notice: {e}")
    print(f"[DB] Initialized database schema at: {DATABASE_URL}")


def drop_db():
    """Drop all tables (useful for test resets)."""
    Base.metadata.drop_all(bind=engine)
    print(f"[DB] Dropped all database tables.")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for clean session lifecycle handling."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_db():
    """FastAPI / Dependency injection friendly session generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
