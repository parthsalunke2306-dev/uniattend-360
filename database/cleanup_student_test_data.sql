-- ============================================================================
-- UNIATTEND 360 - SELECTIVE DATABASE CLEANUP & TEST DATA PURGE SCRIPT
-- Target Database: PostgreSQL 14+ / Supabase
-- Purpose: Safely wipe test students, attendance logs & authenticators while
--          strictly preserving administrative accounts, faculty & curriculum.
-- ============================================================================

-- ============================================================================
-- PART 1: PRE-EXECUTION AUDIT / DRY-RUN (RUN THIS TO PREVIEW COUNTS)
-- ============================================================================
SELECT 
    '1. PRESERVED ACADEMIC INFRASTRUCTURE' AS category,
    (SELECT COUNT(*) FROM universities) AS universities_count,
    (SELECT COUNT(*) FROM colleges) AS colleges_count,
    (SELECT COUNT(*) FROM departments) AS departments_count,
    (SELECT COUNT(*) FROM faculty) AS faculty_count,
    (SELECT COUNT(*) FROM courses) AS courses_count,
    (SELECT COUNT(*) FROM timetable_sessions) AS timetable_sessions_count,
    (SELECT COUNT(*) FROM user_accounts WHERE role != 'STUDENT') AS staff_admin_accounts_count;

SELECT 
    '2. TARGETED STUDENT & ATTENDANCE LEDGER (TO BE WIPED)' AS category,
    (SELECT COUNT(*) FROM students) AS students_count,
    (SELECT COUNT(*) FROM user_accounts WHERE role = 'STUDENT' OR student_id IS NOT NULL) AS student_user_accounts_count,
    (SELECT COUNT(*) FROM bronze_raw_attendance_logs) AS bronze_raw_logs_count,
    (SELECT COUNT(*) FROM silver_fact_attendance) AS silver_fact_attendance_count,
    (SELECT COUNT(*) FROM gold_student_course_summary) AS gold_student_summaries_count,
    (SELECT COUNT(*) FROM proxy_attempt_logs) AS proxy_incidents_count,
    (SELECT COUNT(*) FROM user_passkeys WHERE user_id IN (SELECT id FROM user_accounts WHERE role = 'STUDENT' OR student_id IS NOT NULL)) AS student_passkeys_count,
    (SELECT COUNT(*) FROM user_mfa WHERE user_id IN (SELECT id FROM user_accounts WHERE role = 'STUDENT' OR student_id IS NOT NULL)) AS student_mfa_count,
    (SELECT COUNT(*) FROM user_sessions WHERE user_id IN (SELECT id FROM user_accounts WHERE role = 'STUDENT' OR student_id IS NOT NULL)) AS student_sessions_count;


-- ============================================================================
-- PART 2: ATOMIC TRANSACTIONAL PURGE SCRIPT
-- ============================================================================
DO $$
DECLARE
    v_student_user_ids INT[];
BEGIN
    RAISE NOTICE 'Starting UniAttend 360 Atomic Student Purge...';

    -- Collect student user account IDs for targeted sub-entity deletion
    SELECT ARRAY_AGG(id) INTO v_student_user_ids
    FROM user_accounts
    WHERE role = 'STUDENT' OR student_id IS NOT NULL;

    -- 1. DELETE STUDENT AUTHENTICATORS, PASSKEYS, MFA, RECOVERY CODES & SESSIONS
    IF v_student_user_ids IS NOT NULL AND ARRAY_LENGTH(v_student_user_ids, 1) > 0 THEN
        DELETE FROM user_passkeys WHERE user_id = ANY(v_student_user_ids);
        DELETE FROM user_mfa WHERE user_id = ANY(v_student_user_ids);
        DELETE FROM user_recovery_codes WHERE user_id = ANY(v_student_user_ids);
        DELETE FROM user_sessions WHERE user_id = ANY(v_student_user_ids);
        DELETE FROM security_audit_logs WHERE user_id = ANY(v_student_user_ids);
        
        -- Delete Student Application User Accounts
        DELETE FROM user_accounts WHERE id = ANY(v_student_user_ids);
        RAISE NOTICE 'Purged student user accounts, passkeys, MFA, and active sessions.';
    END IF;

    -- 2. PURGE ATTENDANCE LEDGER & ANALYTICS MARTS (Respecting Dependency Hierarchy)
    DELETE FROM gold_student_course_summary;
    DELETE FROM silver_fact_attendance;
    DELETE FROM bronze_raw_attendance_logs;
    DELETE FROM proxy_attempt_logs;
    RAISE NOTICE 'Purged Gold, Silver, and Bronze attendance logs and proxy attempts.';

    -- 3. PURGE STUDENT DIMENSION RECORDS
    DELETE FROM students;
    RAISE NOTICE 'Purged student dimension table.';

    -- 4. RESET LECTURE SESSION COUNTERS & TEMPLATES
    UPDATE lecture_sessions 
    SET present_count = 0,
        session_status = 'SCHEDULED',
        started_at = NULL,
        paused_at = NULL,
        resumed_at = NULL,
        ended_at = NULL;
    RAISE NOTICE 'Reset lecture sessions counters to 0.';

    -- 5. RESET SERIAL PRIMARY KEY SEQUENCES FOR PURGED TABLES
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'students_id_seq') THEN
        ALTER SEQUENCE students_id_seq RESTART WITH 1;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'silver_fact_attendance_id_seq') THEN
        ALTER SEQUENCE silver_fact_attendance_id_seq RESTART WITH 1;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'bronze_raw_attendance_logs_id_seq') THEN
        ALTER SEQUENCE bronze_raw_attendance_logs_id_seq RESTART WITH 1;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'gold_student_course_summary_id_seq') THEN
        ALTER SEQUENCE gold_student_course_summary_id_seq RESTART WITH 1;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'proxy_attempt_logs_id_seq') THEN
        ALTER SEQUENCE proxy_attempt_logs_id_seq RESTART WITH 1;
    END IF;

    RAISE NOTICE 'UniAttend 360 Student Purge completed successfully.';
END $$;


-- ============================================================================
-- PART 3: SUPABASE AUTH CLEANUP (ONLY APPLICABLE IF USING SUPABASE AUTH.USERS)
-- ============================================================================
-- Deletes student logins from auth.users while safeguarding staff/admin logins
DELETE FROM auth.users 
WHERE (
    raw_user_meta_data->>'role' = 'STUDENT'
    OR email LIKE '%.ds.2024.%'
    OR email LIKE '%student%'
    OR email IN (
        'aarav.sharma@chmc.edu',
        'priya.patel@chmc.edu',
        'rohan.gupta@chmc.edu',
        'ananya.verma@chmc.edu'
    )
)
AND email NOT IN (
    'principal@chmc.edu',
    'shiji.johnson@chmc.edu',
    'razia.khan@chmc.edu',
    'anshul.chimnani@chmc.edu',
    'kalyani.patil@chmc.edu'
);


-- ============================================================================
-- PART 4: POST-EXECUTION SANITY CHECK & HEALTH VERIFICATION
-- ============================================================================

-- A. VERIFY ALL PURGED TABLES ARE ZERO (0)
SELECT 
    (SELECT COUNT(*) FROM students) AS students_count,                      -- Expected: 0
    (SELECT COUNT(*) FROM user_accounts WHERE role = 'STUDENT') AS student_users_count, -- Expected: 0
    (SELECT COUNT(*) FROM silver_fact_attendance) AS attendance_facts_count, -- Expected: 0
    (SELECT COUNT(*) FROM bronze_raw_attendance_logs) AS raw_swipes_count,   -- Expected: 0
    (SELECT COUNT(*) FROM gold_student_course_summary) AS summaries_count,   -- Expected: 0
    (SELECT COUNT(*) FROM proxy_attempt_logs) AS proxy_incidents_count;      -- Expected: 0

-- B. VERIFY ADMINISTRATIVE & CURRICULAR INFRASTRUCTURE IS 100% PRESERVED
SELECT 
    (SELECT COUNT(*) FROM universities) AS preserved_universities,              -- Expected: 1
    (SELECT COUNT(*) FROM colleges) AS preserved_colleges,                      -- Expected: 1
    (SELECT COUNT(*) FROM departments) AS preserved_departments,                -- Expected: 1
    (SELECT COUNT(*) FROM faculty) AS preserved_faculty,                        -- Expected: 3
    (SELECT COUNT(*) FROM courses) AS preserved_courses,                        -- Expected: 8
    (SELECT COUNT(*) FROM timetable_sessions) AS preserved_timetable_sessions,  -- Expected: 14
    (SELECT COUNT(*) FROM user_accounts WHERE role != 'STUDENT') AS preserved_staff_accounts; -- Expected: 5

-- C. AUDIT ACTIVE ADMINISTRATIVE USER ACCOUNTS
SELECT id, username, email, full_name, role, is_active, mfa_enabled 
FROM user_accounts 
WHERE role != 'STUDENT'
ORDER BY id ASC;
