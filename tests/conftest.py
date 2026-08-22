"""
Pytest configuration for UniAttend 360 test suite.
Ensures tests run in an isolated SQLite test environment, protecting production cloud DBs.
"""

import os
import sys

# Point to isolated SQLite test database for all pytest executions
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_uniattend.db")
os.environ["UNIATTEND_DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from database.db_manager import init_db, drop_db, get_db_session
from data.data_generator import seed_chmc_academics, seed_chmc_user_accounts, generate_chmc_attendance_stream

@pytest.fixture(scope="session", autouse=True)
def setup_global_test_db():
    """Initializes and seeds the isolated test database for the entire test session."""
    drop_db()
    init_db()
    with get_db_session() as session:
        seed_chmc_academics(session)
        seed_chmc_user_accounts(session)
        generate_chmc_attendance_stream(session, weeks=4)
    yield
    drop_db()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
