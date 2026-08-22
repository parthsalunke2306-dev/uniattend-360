"""
Automated Supabase / Cloud PostgreSQL Setup & Migration Script for UniAttend 360.
Usage:
    python scripts/connect_supabase.py [OPTIONAL_DATABASE_URI]
"""

import os
import sys
from dotenv import load_dotenv

# Set UTF-8 encoding for standard output on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

def setup_cloud_db(db_url: str = None):
    if db_url:
        os.environ["UNIATTEND_DATABASE_URL"] = db_url

    # Refresh db_manager engine
    from database import db_manager
    from database.models import UserAccount, Student, Faculty, Department, Course
    from data.data_generator import seed_chmc_academics, seed_chmc_user_accounts, generate_chmc_attendance_stream

    target_url = os.environ.get("UNIATTEND_DATABASE_URL", db_manager.DEFAULT_DB_URL)
    masked_url = target_url.split("@")[-1] if "@" in target_url else target_url

    print("=" * 60)
    print(f"[DB SETUP] Connecting to Database: {masked_url}")
    print("=" * 60)

    try:
        print("\n1. Initializing schema and tables in database...")
        db_manager.init_db()
        print("   [OK] Schema and tables created successfully.")

        print("\n2. Seeding Smt. C.H.M. College Second Year Data Science hierarchy...")
        with db_manager.get_db_session() as db:
            seed_chmc_academics(db)
            seed_chmc_user_accounts(db)
            generate_chmc_attendance_stream(db, weeks=4)
        print("   [OK] Academics, 8 course units, and user accounts seeded.")

        print("\n3. Verifying live database records...")
        with db_manager.get_db_session() as db:
            users = db.query(UserAccount).all()
            print(f"   [SUMMARY] Total Registered Accounts: {len(users)}")
            for u in users:
                print(f"      - {u.full_name} | Email: {u.email} | Role: {u.role}")

        print("\n" + "=" * 60)
        print("[SUCCESS] Database is fully active, migrated, and ready for production!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Failed to connect to database: {e}")
        print("Please verify your connection URI and password.")
        sys.exit(1)

if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else None
    setup_cloud_db(url_arg)
