"""
Database Connection Manager and Session Factory for UniAttend Analytics.
Handles database initialization, engine management, session pooling, and utility helpers.
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

# Default SQLite database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "uniattend.db")
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_PATH}"

# Connection string can be overridden by environment variable for PostgreSQL / MySQL
DATABASE_URL = os.environ.get("UNIATTEND_DATABASE_URL", DEFAULT_DB_URL)

# Configure engine (SQLite requires check_same_thread=False for multi-threaded apps like Streamlit)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # Set to True for SQL query debugging
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all database tables defined in the metadata."""
    Base.metadata.create_all(bind=engine)
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
