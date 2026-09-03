-- ============================================================================
-- UNIATTEND 360 - SUPABASE SCHEMATIC RESTRUCTURING & WEBAUTHN MIGRATION
-- Architecture: Strict 1:1 FIDO2 Hardware Binding & Admin Device Reset Flow
-- Target Engine: PostgreSQL 15+ / Supabase
-- Applied Date: 2026-09-04
-- ============================================================================

-- ----------------------------------------------------------------------------
-- STEP 1: ENUM TYPES CREATION (Idempotent)
-- ----------------------------------------------------------------------------

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_enum') THEN
        CREATE TYPE user_role_enum AS ENUM (
            'STUDENT', 
            'TEACHER', 
            'COORDINATOR', 
            'ADMIN', 
            'PRINCIPAL'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'device_reset_status_enum') THEN
        CREATE TYPE device_reset_status_enum AS ENUM (
            'NONE', 
            'PENDING'
        );
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- STEP 2: RESTRUCTURE USERS TABLE (user_accounts)
-- ----------------------------------------------------------------------------

ALTER TABLE user_accounts 
    ADD COLUMN IF NOT EXISTS device_reset_status VARCHAR(20) DEFAULT 'NONE',
    ADD COLUMN IF NOT EXISTS is_device_bound BOOLEAN DEFAULT FALSE NOT NULL,
    ADD COLUMN IF NOT EXISTS bound_device_name VARCHAR(150),
    ADD COLUMN IF NOT EXISTS bound_device_uuid VARCHAR(150);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_user_device_reset_status'
    ) THEN
        ALTER TABLE user_accounts 
            ADD CONSTRAINT chk_user_device_reset_status 
            CHECK (device_reset_status IN ('NONE', 'PENDING'));
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- STEP 3: STRICT 1:1 WEBAUTHN PASSKEYS TABLE
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS passkeys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    credential_id VARCHAR(255) NOT NULL UNIQUE,
    public_key TEXT NOT NULL,
    counter INTEGER DEFAULT 0 NOT NULL,
    device_name VARCHAR(150) DEFAULT 'Primary Mobile Handset',
    transports VARCHAR(100) DEFAULT 'internal',
    aaguid VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- CRITICAL DATABASE CONSTRAINT: Exactly 1 passkey per student account
    CONSTRAINT uq_passkeys_user_id UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_passkeys_user_id ON passkeys(user_id);
CREATE INDEX IF NOT EXISTS idx_passkeys_credential_id ON passkeys(credential_id);

-- ----------------------------------------------------------------------------
-- STEP 4: RESTRUCTURE ATTENDANCE TABLES (silver_fact_attendance)
-- ----------------------------------------------------------------------------

ALTER TABLE silver_fact_attendance 
    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES user_accounts(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS lecture_session_id VARCHAR(100) REFERENCES lecture_sessions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS biometrically_verified BOOLEAN DEFAULT FALSE NOT NULL,
    ADD COLUMN IF NOT EXISTS passkey_id INTEGER REFERENCES passkeys(id) ON DELETE SET NULL;

UPDATE silver_fact_attendance sfa
SET user_id = ua.id
FROM user_accounts ua
WHERE sfa.student_id = ua.student_id AND sfa.user_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_sfa_user_biometric 
    ON silver_fact_attendance(user_id, biometrically_verified);

-- ----------------------------------------------------------------------------
-- STEP 5: ROW LEVEL SECURITY (RLS) POLICIES
-- ----------------------------------------------------------------------------

ALTER TABLE passkeys ENABLE ROW LEVEL SECURITY;
ALTER TABLE silver_fact_attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION get_current_user_role()
RETURNS VARCHAR AS $$
    SELECT role FROM user_accounts 
    WHERE id::text = auth.uid()::text 
       OR email = auth.jwt() ->> 'email'
       OR username = auth.jwt() ->> 'sub'
    LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS INTEGER AS $$
    SELECT id FROM user_accounts 
    WHERE id::text = auth.uid()::text 
       OR email = auth.jwt() ->> 'email'
       OR username = auth.jwt() ->> 'sub'
    LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- RLS POLICIES FOR: passkeys
DROP POLICY IF EXISTS "Students can view own passkey" ON passkeys;
CREATE POLICY "Students can view own passkey" ON passkeys
    FOR SELECT
    USING (
        user_id = get_current_user_id() 
        OR get_current_user_role() IN ('ADMIN', 'ADMIN_STAFF', 'PRINCIPAL')
        OR auth.uid() IS NULL
    );

DROP POLICY IF EXISTS "Students can enroll own passkey" ON passkeys;
CREATE POLICY "Students can enroll own passkey" ON passkeys
    FOR INSERT
    WITH CHECK (
        user_id = get_current_user_id()
        OR auth.uid() IS NULL
    );

DROP POLICY IF EXISTS "Admins can delete passkeys during reset" ON passkeys;
CREATE POLICY "Admins can delete passkeys during reset" ON passkeys
    FOR DELETE
    USING (
        get_current_user_role() IN ('ADMIN', 'ADMIN_STAFF', 'PRINCIPAL')
        OR auth.uid() IS NULL
    );

-- RLS POLICIES FOR: silver_fact_attendance
DROP POLICY IF EXISTS "Students view own attendance; Staff view all" ON silver_fact_attendance;
CREATE POLICY "Students view own attendance; Staff view all" ON silver_fact_attendance
    FOR SELECT
    USING (
        user_id = get_current_user_id() 
        OR get_current_user_role() IN ('TEACHER', 'COORDINATOR', 'ADMIN', 'PRINCIPAL')
        OR auth.uid() IS NULL
    );

DROP POLICY IF EXISTS "Students insert own verified attendance" ON silver_fact_attendance;
CREATE POLICY "Students insert own verified attendance" ON silver_fact_attendance
    FOR INSERT
    WITH CHECK (
        user_id = get_current_user_id()
        OR auth.uid() IS NULL
    );

DROP POLICY IF EXISTS "Faculty and Admins can update attendance records" ON silver_fact_attendance;
CREATE POLICY "Faculty and Admins can update attendance records" ON silver_fact_attendance
    FOR UPDATE
    USING (
        get_current_user_role() IN ('TEACHER', 'COORDINATOR', 'ADMIN', 'PRINCIPAL')
        OR auth.uid() IS NULL
    );

-- RLS POLICIES FOR: user_accounts
DROP POLICY IF EXISTS "Users view own profile; Admins view all" ON user_accounts;
CREATE POLICY "Users view own profile; Admins view all" ON user_accounts
    FOR SELECT
    USING (
        id = get_current_user_id() 
        OR get_current_user_role() IN ('TEACHER', 'COORDINATOR', 'ADMIN', 'PRINCIPAL')
        OR auth.uid() IS NULL
    );

DROP POLICY IF EXISTS "Students can request device reset" ON user_accounts;
CREATE POLICY "Students can request device reset" ON user_accounts
    FOR UPDATE
    USING (
        id = get_current_user_id() 
        OR get_current_user_role() IN ('ADMIN', 'ADMIN_STAFF', 'PRINCIPAL')
        OR auth.uid() IS NULL
    )
    WITH CHECK (
        device_reset_status IN ('NONE', 'PENDING')
    );

DROP POLICY IF EXISTS "Admins manage all user accounts" ON user_accounts;
CREATE POLICY "Admins manage all user accounts" ON user_accounts
    FOR ALL
    USING (
        get_current_user_role() IN ('ADMIN', 'ADMIN_STAFF', 'PRINCIPAL')
        OR auth.uid() IS NULL
    );
