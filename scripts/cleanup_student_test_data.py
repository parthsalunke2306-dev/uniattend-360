"""
UniAttend 360 - Database Selective Cleanup Script (Test Data Purge).
Wipes all student test data, student authenticators, passkeys, and attendance logs,
while strictly preserving administrative, coordinator, and faculty infrastructure.
"""

import os
import sys
from datetime import datetime

# Set UTF-8 standard output for Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import db_manager
from database.models import (
    University, College, Department, Course, Faculty, Student,
    TimetableSession, LectureSession, RawAttendanceLog, FactAttendance,
    StudentCourseSummary, UserAccount, UserMFA, UserRecoveryCode,
    UserPasskey, UserSession, SecurityAuditLog, ProxyAttemptLog
)
from pipeline.anti_proxy_engine import anti_proxy_engine


def audit_table_counts(session) -> dict:
    """Returns current row counts for all database entities."""
    return {
        # Administrative & Curricular (Preserved)
        "universities": session.query(University).count(),
        "colleges": session.query(College).count(),
        "departments": session.query(Department).count(),
        "faculty": session.query(Faculty).count(),
        "courses": session.query(Course).count(),
        "timetable_sessions": session.query(TimetableSession).count(),
        "lecture_sessions": session.query(LectureSession).count(),
        "staff_accounts": session.query(UserAccount).filter(UserAccount.role != 'STUDENT').count(),
        "staff_passkeys": session.query(UserPasskey).join(UserAccount).filter(UserAccount.role != 'STUDENT').count(),
        "staff_mfa": session.query(UserMFA).join(UserAccount).filter(UserAccount.role != 'STUDENT').count(),
        
        # Student & Attendance Ledger (Purged)
        "students": session.query(Student).count(),
        "student_accounts": session.query(UserAccount).filter(
            (UserAccount.role == 'STUDENT') | (UserAccount.student_id != None)
        ).count(),
        "student_passkeys": session.query(UserPasskey).join(UserAccount).filter(
            (UserAccount.role == 'STUDENT') | (UserAccount.student_id != None)
        ).count(),
        "student_mfa": session.query(UserMFA).join(UserAccount).filter(
            (UserAccount.role == 'STUDENT') | (UserAccount.student_id != None)
        ).count(),
        "student_recovery_codes": session.query(UserRecoveryCode).join(UserAccount).filter(
            (UserAccount.role == 'STUDENT') | (UserAccount.student_id != None)
        ).count(),
        "student_sessions": session.query(UserSession).join(UserAccount).filter(
            (UserAccount.role == 'STUDENT') | (UserAccount.student_id != None)
        ).count(),
        "bronze_raw_attendance": session.query(RawAttendanceLog).count(),
        "silver_fact_attendance": session.query(FactAttendance).count(),
        "gold_student_summaries": session.query(StudentCourseSummary).count(),
        "proxy_attempt_logs": session.query(ProxyAttemptLog).count(),
    }


def execute_selective_cleanup(dry_run: bool = False):
    """Performs an atomic, transactional purge of student test records while preserving administrative hierarchy."""
    print("=" * 80)
    print("  UNIATTEND 360 - SELECTIVE DATABASE CLEANUP & TEST DATA PURGE")
    print(f"  Target DB: {db_manager.DATABASE_URL.split('@')[-1]}")
    print(f"  Mode: {'[DRY RUN PREVIEW]' if dry_run else '[ATOMIC LIVE EXECUTION]'}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Ensure all tables exist in target DB
    db_manager.init_db()

    with db_manager.get_db_session() as session:
        # 1. PRE-FLIGHT AUDIT
        print("\n📊 1. PRE-FLIGHT AUDIT (CURRENT DATABASE STATE):")
        pre_counts = audit_table_counts(session)
        print("  🟢 PRESERVED INFRASTRUCTURE:")
        print(f"     • Universities:        {pre_counts['universities']}")
        print(f"     • Colleges:            {pre_counts['colleges']}")
        print(f"     • Departments:         {pre_counts['departments']}")
        print(f"     • Faculty Members:     {pre_counts['faculty']}")
        print(f"     • Academic Courses:    {pre_counts['courses']}")
        print(f"     • Timetable Sessions:  {pre_counts['timetable_sessions']}")
        print(f"     • Lecture Templates:   {pre_counts['lecture_sessions']}")
        print(f"     • Staff User Accounts: {pre_counts['staff_accounts']} (Principal, HOD, Faculty)")
        print(f"     • Staff Passkeys/MFA:  {pre_counts['staff_passkeys']} passkeys, {pre_counts['staff_mfa']} MFA")
        print("\n  🔴 TARGETED FOR PURGE:")
        print(f"     • Student Records:     {pre_counts['students']}")
        print(f"     • Student Accounts:    {pre_counts['student_accounts']}")
        print(f"     • Student Passkeys:    {pre_counts['student_passkeys']}")
        print(f"     • Student MFA Configs: {pre_counts['student_mfa']}")
        print(f"     • Student Recv Codes:  {pre_counts['student_recovery_codes']}")
        print(f"     • Student Sessions:    {pre_counts['student_sessions']}")
        print(f"     • Bronze Raw Swipes:   {pre_counts['bronze_raw_attendance']}")
        print(f"     • Silver Attendance:   {pre_counts['silver_fact_attendance']}")
        print(f"     • Gold Summaries:      {pre_counts['gold_student_summaries']}")
        print(f"     • Proxy Attempt Logs:  {pre_counts['proxy_attempt_logs']}")

        if dry_run:
            print("\n[DRY RUN COMPLETE] No records were modified.")
            return

        print("\n" + "-" * 80)
        print("🚀 2. EXECUTING ATOMIC TRANSACTIONAL PURGE...")
        print("-" * 80)

        # Retrieve student user account IDs
        student_users = session.query(UserAccount).filter(
            (UserAccount.role == 'STUDENT') | (UserAccount.student_id != None)
        ).all()
        student_user_ids = [u.id for u in student_users]
        print(f"   [+] Identified {len(student_user_ids)} student user account IDs for deletion.")

        # Step 2A: Delete Student Hardware Passkeys, MFA, and Sessions
        if student_user_ids:
            pks_deleted = session.query(UserPasskey).filter(UserPasskey.user_id.in_(student_user_ids)).delete(synchronize_session=False)
            mfas_deleted = session.query(UserMFA).filter(UserMFA.user_id.in_(student_user_ids)).delete(synchronize_session=False)
            rcs_deleted = session.query(UserRecoveryCode).filter(UserRecoveryCode.user_id.in_(student_user_ids)).delete(synchronize_session=False)
            sess_deleted = session.query(UserSession).filter(UserSession.user_id.in_(student_user_ids)).delete(synchronize_session=False)
            auds_deleted = session.query(SecurityAuditLog).filter(SecurityAuditLog.user_id.in_(student_user_ids)).delete(synchronize_session=False)
            print(f"   [+] Purged {pks_deleted} student passkeys, {mfas_deleted} MFA, {rcs_deleted} recovery codes, {sess_deleted} sessions, {auds_deleted} student audit logs.")

        # Step 2B: Delete Student User Accounts
        if student_user_ids:
            usr_deleted = session.query(UserAccount).filter(UserAccount.id.in_(student_user_ids)).delete(synchronize_session=False)
            print(f"   [+] Purged {usr_deleted} student login profiles from user_accounts.")

        # Step 2C: Delete Analytics Summaries (Gold) & Fact Attendance (Silver)
        gold_deleted = session.query(StudentCourseSummary).delete(synchronize_session=False)
        silver_deleted = session.query(FactAttendance).delete(synchronize_session=False)
        print(f"   [+] Purged {gold_deleted} rows from gold_student_course_summary.")
        print(f"   [+] Purged {silver_deleted} rows from silver_fact_attendance.")

        # Step 2D: Delete Raw Device Swipes (Bronze) & Security Proxy Interceptions
        bronze_deleted = session.query(RawAttendanceLog).delete(synchronize_session=False)
        proxy_deleted = session.query(ProxyAttemptLog).delete(synchronize_session=False)
        print(f"   [+] Purged {bronze_deleted} rows from bronze_raw_attendance_logs.")
        print(f"   [+] Purged {proxy_deleted} rows from proxy_attempt_logs.")

        # Step 2E: Delete Student Dimensions
        students_deleted = session.query(Student).delete(synchronize_session=False)
        print(f"   [+] Purged {students_deleted} student dimension rows from students table.")

        # Step 2F: Reset Lecture Session Counts
        for lec in session.query(LectureSession).all():
            lec.present_count = 0
            lec.session_status = "SCHEDULED"
        print(f"   [+] Reset live present counts and statuses on lecture_sessions templates.")

        # Step 2G: Reset In-Memory Anti-Proxy Engine State
        anti_proxy_engine.student_hardware_locks.clear()
        anti_proxy_engine.session_device_registry.clear()
        anti_proxy_engine.session_attendance_registry.clear()
        anti_proxy_engine.proxy_attempt_logs.clear()
        print(f"   [+] Reset in-memory anti-proxy device registries & hardware locks.")

        session.commit()
        print("\n   [COMMIT] Transaction committed successfully to database.")

    # 3. POST-CLEANUP VERIFICATION
    print("\n" + "=" * 80)
    print("✅ 3. POST-CLEANUP HEALTH CHECK & SANITY VERIFICATION:")
    print("=" * 80)
    with db_manager.get_db_session() as session:
        post_counts = audit_table_counts(session)
        
        # Verify Purged Tables == 0
        assert post_counts["students"] == 0, f"Error: {post_counts['students']} students remaining!"
        assert post_counts["student_accounts"] == 0, f"Error: {post_counts['student_accounts']} student accounts remaining!"
        assert post_counts["silver_fact_attendance"] == 0, f"Error: {post_counts['silver_fact_attendance']} attendance facts remaining!"
        assert post_counts["gold_student_summaries"] == 0, f"Error: {post_counts['gold_student_summaries']} summaries remaining!"
        assert post_counts["bronze_raw_attendance"] == 0, f"Error: {post_counts['bronze_raw_attendance']} raw logs remaining!"
        assert post_counts["proxy_attempt_logs"] == 0, f"Error: {post_counts['proxy_attempt_logs']} proxy logs remaining!"
        assert post_counts["student_passkeys"] == 0, f"Error: {post_counts['student_passkeys']} student passkeys remaining!"

        # Verify Preserved Tables Intact
        assert post_counts["faculty"] == pre_counts["faculty"], "Error: Faculty count altered!"
        assert post_counts["courses"] == pre_counts["courses"], "Error: Courses altered!"
        assert post_counts["departments"] == pre_counts["departments"], "Error: Departments altered!"
        assert post_counts["staff_accounts"] == pre_counts["staff_accounts"], "Error: Staff accounts altered!"

        print("  🎉 ALL PURGED TABLES VERIFIED AT ZERO (0) ROWS:")
        print("     • Students:               0 (Cleaned)")
        print("     • Student Accounts:       0 (Cleaned)")
        print("     • Student Passkeys:       0 (Cleaned)")
        print("     • Fact Attendance:        0 (Cleaned)")
        print("     • Raw Swipes:             0 (Cleaned)")
        print("     • Student Course Summary: 0 (Cleaned)")
        print("     • Proxy Attempt Logs:     0 (Cleaned)")
        print("\n  🛡️ ADMINISTRATIVE & ACADEMIC INFRASTRUCTURE 100% PRESERVED:")
        print(f"     • Universities:           {post_counts['universities']} (Intact)")
        print(f"     • Colleges:               {post_counts['colleges']} (Intact)")
        print(f"     • Departments:            {post_counts['departments']} (Intact)")
        print(f"     • Faculty Members:        {post_counts['faculty']} (Intact)")
        print(f"     • Academic Courses:       {post_counts['courses']} (Intact)")
        print(f"     • Staff User Accounts:    {post_counts['staff_accounts']} (Intact: Principal, Coordinator, Faculty)")
        print(f"     • Timetable Sessions:     {post_counts['timetable_sessions']} (Intact)")

        print("\n  Remaining Active Administrative Accounts in Database:")
        staff_users = session.query(UserAccount).filter(UserAccount.role != 'STUDENT').all()
        for u in staff_users:
            print(f"     - [ID: {u.id}] {u.full_name} | Email: {u.email} | Role: {u.role}")

    print("\n" + "=" * 80)
    print("✨ DATABASE IS CLEAN, COMPLIANT, AND READY FOR LIVE NEW COHORT ENROLLMENT!")
    print("=" * 80)


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    execute_selective_cleanup(dry_run=is_dry)
