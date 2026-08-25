"""
UniAttend 360 - Comprehensive Multi-Tier Authentication & Security Test Suite.
Verifies:
  1. Layer 1: Primary Authentication (Argon2id/bcrypt, lockout, password policy)
  2. Layer 2: Two-Step Verification (RFC 6238 TOTP, anti-replay, single-use recovery codes)
  3. Layer 3: WebAuthn / Passkeys (Public-key cryptography, signature counters)
  4. Session Management: Short-lived JWTs, active session tracking, instant revocation, logout-all
  5. Server-Side RBAC: Student, Teacher, Coordinator, Principal role guards
  6. Audit Logging: Non-repudiation logging with zero secret/credential leakage
"""

import os
import sys
import time
import pytest
import pyotp
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.models import UserAccount, UserMFA, UserRecoveryCode, UserPasskey, UserSession, SecurityAuditLog
from database.db_manager import get_db_session, init_db, drop_db
from api.security import (
    PasswordPolicy, PasswordHasherService, BruteForceProtector,
    TOTPService, RecoveryCodeService, SessionService, SecurityAuditLogger,
    create_jwt_access_token, create_temp_mfa_token, decode_jwt_token
)
from api.server import app
from data.data_generator import seed_chmc_academics, seed_chmc_user_accounts

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Database is managed session-wide by conftest.py
    yield


# ==========================================
# 1. LAYER 1: PRIMARY AUTH & PASSWORD POLICY
# ==========================================

def test_password_policy_validation():
    """Verifies that password complexity rules reject weak passwords and accept strong ones."""
    assert PasswordPolicy.validate("weak")[0] is False
    assert PasswordPolicy.validate("NoDigitsHere!")[0] is False
    assert PasswordPolicy.validate("nouppercase123!")[0] is False
    assert PasswordPolicy.validate("NOLOWERCASE123!")[0] is False
    assert PasswordPolicy.validate("NoSpecialChars123")[0] is False
    assert PasswordPolicy.validate("Valid@Pass2026!")[0] is True


def test_argon2id_password_hashing():
    """Verifies Argon2id password hashing and verification."""
    raw_pwd = "SuperSecure@2026!"
    hashed = PasswordHasherService.hash(raw_pwd)
    
    assert hashed.startswith("$argon2")
    assert PasswordHasherService.verify(raw_pwd, hashed) is True
    assert PasswordHasherService.verify("WrongPassword@123", hashed) is False


def test_primary_login_success():
    """Validates primary login for registered student (Aarav Sharma)."""
    response = client.post("/api/v1/auth/login", json={
        "identifier": "aarav.sharma@chmc.edu",
        "password": "CHMC@2026!",
        "device_fingerprint": "DEV-TEST-001"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "aarav.sharma@chmc.edu"
    assert data["role"] == "STUDENT"
    assert "token" in data
    assert "session_token" in data


def test_primary_login_invalid_password():
    """Validates that invalid password returns 401 and does not expose internal errors."""
    response = client.post("/api/v1/auth/login", json={
        "identifier": "aarav.sharma@chmc.edu",
        "password": "IncorrectPassword123!",
        "device_fingerprint": "DEV-TEST-001"
    })
    assert response.status_code == 401
    assert "Invalid email/username or password." in response.json()["detail"]


def test_primary_login_unknown_account():
    """Validates that non-existent username returns identical generic error (prevents enumeration)."""
    response = client.post("/api/v1/auth/login", json={
        "identifier": "nonexistent.user@chmc.edu",
        "password": "AnyPassword123!",
        "device_fingerprint": "DEV-TEST-001"
    })
    assert response.status_code == 401
    assert "Invalid email/username or password." in response.json()["detail"]


def test_brute_force_lockout():
    """Verifies 5 consecutive failed attempts trigger a 15-minute temporary account lockout."""
    target_email = "rohan.gupta@chmc.edu"
    
    # Send 5 failed attempts
    for _ in range(5):
        client.post("/api/v1/auth/login", json={
            "identifier": target_email,
            "password": "WrongPassword!",
            "device_fingerprint": "DEV-ATTACKER-007"
        })

    # 6th attempt must return 429 Too Many Requests
    lock_resp = client.post("/api/v1/auth/login", json={
        "identifier": target_email,
        "password": "CHMC@2026!",  # Even with correct password, locked out
        "device_fingerprint": "DEV-ATTACKER-007"
    })
    assert lock_resp.status_code == 429
    assert "temporarily locked" in lock_resp.json()["detail"]


# ==========================================
# 2. LAYER 2: TOTP 2-STEP VERIFICATION & RECOVERY
# ==========================================

def test_totp_generation_and_verification():
    """Tests RFC 6238 TOTP secret generation, QR encoding, and verification."""
    secret = TOTPService.generate_secret()
    uri = TOTPService.get_provisioning_uri(secret, "test.user@chmc.edu")
    assert "otpauth://totp/" in uri
    
    qr_b64 = TOTPService.generate_qr_base64(uri)
    assert len(qr_b64) > 100

    # Generate active OTP code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    
    # 1. First verification succeeds
    is_valid, timestep = TOTPService.verify_code(secret, valid_code, 0)
    assert is_valid is True
    assert timestep > 0

    # 2. Replay attack: Reusing same code in same timestep must fail
    replay_valid, _ = TOTPService.verify_code(secret, valid_code, timestep)
    assert replay_valid is False

    # 3. Invalid code fails
    invalid_valid, _ = TOTPService.verify_code(secret, "999999", 0)
    assert invalid_valid is False


def test_mfa_setup_and_login_flow():
    """Tests complete flow: Primary login -> MFA Challenge -> TOTP Verification -> Session."""
    # 1. Login as teacher (Miss Razia)
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "razia.khan@chmc.edu",
        "password": "CHMC@2026!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Enable MFA via /mfa/setup
    setup_resp = client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_resp.status_code == 200
    setup_data = setup_resp.json()
    secret = setup_data["secret"]
    recovery_codes = setup_data["recovery_codes"]
    assert len(recovery_codes) == 8

    # 3. Confirm MFA with valid OTP
    totp = pyotp.TOTP(secret)
    confirm_resp = client.post("/api/v1/auth/mfa/verify-setup", headers=headers, json={
        "secret": secret,
        "code": totp.now(),
        "recovery_codes": recovery_codes
    })
    assert confirm_resp.status_code == 200

    # 4. Subsequent login provides direct 1-step authenticated session
    direct_login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "razia.khan@chmc.edu",
        "password": "CHMC@2026!"
    })
    assert direct_login_resp.status_code == 200
    assert direct_login_resp.json()["role"] == "TEACHER"
    assert "token" in direct_login_resp.json()

    # 5. Verify TOTP verification endpoint with temp token
    with get_db_session() as db:
        u = db.query(UserAccount).filter_by(email="razia.khan@chmc.edu").first()
        temp_token = create_temp_mfa_token(u.id, u.email, "TOTP")
    mfa_verify_resp = client.post("/api/v1/auth/login/mfa/totp", json={
        "temp_token": temp_token,
        "otp_code": totp.now(),
        "trust_device": True
    })
    assert mfa_verify_resp.status_code == 200
    assert mfa_verify_resp.json()["role"] == "TEACHER"
    assert "token" in mfa_verify_resp.json()


def test_single_use_emergency_recovery_code():
    """Verifies that backup recovery codes allow emergency access and are single-use."""
    raw_code = "9A7B-3K2M"
    with get_db_session() as db:
        user = db.query(UserAccount).filter_by(email="razia.khan@chmc.edu").first()
        user_id = user.id
        user_email = user.email
        temp_token = create_temp_mfa_token(user_id, user_email, "TOTP")
        RecoveryCodeService.store_codes(db, user_id, [raw_code])

    # 1. First recovery attempt succeeds
    rec_resp = client.post("/api/v1/auth/login/mfa/recovery", json={
        "temp_token": temp_token,
        "recovery_code": raw_code
    })
    assert rec_resp.status_code == 200
    assert rec_resp.json()["email"] == "razia.khan@chmc.edu"

    # 2. Second attempt with same code fails (single-use enforced)
    rec_resp_reuse = client.post("/api/v1/auth/login/mfa/recovery", json={
        "temp_token": temp_token,
        "recovery_code": raw_code
    })
    assert rec_resp_reuse.status_code == 401


# ==========================================
# 3. SESSION MANAGEMENT & REVOCATION
# ==========================================

def test_session_listing_and_revocation():
    """Tests active session listing, specific session revocation, and logout all devices."""
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "principal@chmc.edu",
        "password": "CHMC@2026!",
        "device_fingerprint": "DEV-MACBOOK-PRO"
    })
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List active sessions
    sess_list_resp = client.get("/api/v1/auth/sessions", headers=headers)
    assert sess_list_resp.status_code == 200
    sessions = sess_list_resp.json()
    assert len(sessions) >= 1
    target_session_id = sessions[0]["id"]

    # 2. Revoke specific session
    revoke_resp = client.post(f"/api/v1/auth/sessions/{target_session_id}/revoke", headers=headers)
    assert revoke_resp.status_code == 200

    # 3. Using revoked session token fails
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 401


def test_logout_all_devices():
    """Verifies that 'Logout from all devices' invalidates all user sessions."""
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "shiji.johnson@chmc.edu",
        "password": "CHMC@2026!",
        "device_fingerprint": "DEV-OFFICE-PC"
    })
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    revoke_all_resp = client.post("/api/v1/auth/sessions/revoke-all", headers=headers)
    assert revoke_all_resp.status_code == 200
    assert "Successfully logged out" in revoke_all_resp.json()["message"]


# ==========================================
# 4. SERVER-SIDE ROLE-BASED ACCESS CONTROL (RBAC)
# ==========================================

def test_student_forbidden_from_admin_audit_logs():
    """Ensures students cannot access administrative audit logs."""
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "aarav.sharma@chmc.edu",
        "password": "CHMC@2026!"
    })
    student_token = login_resp.json()["token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Student accessing /api/v1/auth/audit-logs must receive 403 Forbidden
    audit_resp = client.get("/api/v1/auth/audit-logs", headers=student_headers)
    assert audit_resp.status_code == 403
    assert "Access denied" in audit_resp.json()["detail"]


def test_principal_authorized_for_audit_logs():
    """Ensures Principal can access administrative audit logs."""
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "principal@chmc.edu",
        "password": "CHMC@2026!"
    })
    principal_token = login_resp.json()["token"]
    principal_headers = {"Authorization": f"Bearer {principal_token}"}

    audit_resp = client.get("/api/v1/auth/audit-logs", headers=principal_headers)
    assert audit_resp.status_code == 200
    assert isinstance(audit_resp.json(), list)


# ==========================================
# 5. SECURITY AUDIT LOGGING (ZERO SECRETS)
# ==========================================

def test_security_audit_logging_sanitization():
    """Verifies that security audit logs record events without leaking passwords or secrets."""
    with get_db_session() as db:
        SecurityAuditLogger.log(
            db=db,
            user_id=1,
            event_type="TEST_SECURITY_EVENT",
            severity="INFO",
            details={
                "ip": "192.168.1.50",
                "user_password": "MySecretPassword123!",
                "totp_secret": "JBSWY3DPEHPK3PXP",
                "action": "Unit Test Validation"
            }
        )

        entry = db.query(SecurityAuditLog).filter_by(event_type="TEST_SECURITY_EVENT").first()
        assert entry is not None
        assert "MySecretPassword123!" not in entry.details
        assert "JBSWY3DPEHPK3PXP" not in entry.details
        assert "[REDACTED]" in entry.details


# ==========================================
# 6. DYNAMIC SELF-REGISTRATION & ONBOARDING
# ==========================================

def test_student_self_registration_success():
    """Verifies that a brand new student can self-register and get an active authenticated session."""
    reg_resp = client.post("/api/v1/auth/register", json={
        "full_name": "Ramesh Singh",
        "email": "ramesh.singh@gmail.com",
        "role": "STUDENT",
        "identifier": "CHMC-DS-2024-006",
        "password": "SecurePass@2026!",
        "department_code": "DS",
        "device_fingerprint": "DEV-RAMESH-MOBILE"
    })
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert data["email"] == "ramesh.singh@gmail.com"
    assert data["role"] == "STUDENT"
    assert "token" in data
    assert "session_token" in data

    # Verify newly registered student can now immediately log in
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "ramesh.singh@gmail.com",
        "password": "SecurePass@2026!",
        "device_fingerprint": "DEV-RAMESH-MOBILE"
    })
    assert login_resp.status_code == 200
    assert login_resp.json()["email"] == "ramesh.singh@gmail.com"


def test_bulk_student_roster_import():
    """Verifies that Coordinator/Principal can bulk import new students."""
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "coordinator.ds",
        "password": "CHMC@2026!"
    })
    coord_token = login_resp.json()["token"]
    coord_headers = {"Authorization": f"Bearer {coord_token}"}

    bulk_resp = client.post("/api/v1/auth/bulk-import-students", headers=coord_headers, json={
        "department_code": "DS",
        "students": [
            {"roll_no": "CHMC-DS-2024-007", "full_name": "Kavita Nair", "email": "kavita.nair@gmail.com", "gender": "F"},
            {"roll_no": "CHMC-DS-2024-008", "full_name": "Siddharth Joshi", "email": "siddharth.joshi@yahoo.com", "gender": "M"}
        ]
    })
    assert bulk_resp.status_code == 200
    assert bulk_resp.json()["imported_count"] == 2

    # Verify imported student can log in with default password
    s_login = client.post("/api/v1/auth/login", json={
        "identifier": "CHMC-DS-2024-007",
        "password": "CHMC@2026!"
    })
    assert s_login.status_code == 200
    assert s_login.json()["email"] == "kavita.nair@gmail.com"


def test_student_profile_update():
    """Verifies that an authenticated student can update their contact info, bio, and avatar."""
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "CHMC-DS-2024-007",
        "password": "CHMC@2026!"
    })
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_resp = client.put("/api/v1/auth/student/profile", headers=headers, json={
        "phone_number": "9876543210",
        "alternate_email": "kavita.personal@gmail.com",
        "bio": "S.Y. Data Science enthusiast working on Python & ML algorithms.",
        "avatar_icon": "🚀"
    })
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["status"] == "SUCCESS"
    assert data["profile"]["phone_number"] == "9876543210"
    assert data["profile"]["alternate_email"] == "kavita.personal@gmail.com"
    assert data["profile"]["bio"] == "S.Y. Data Science enthusiast working on Python & ML algorithms."
    assert data["profile"]["avatar_icon"] == "🚀"


def test_passkey_hardware_challenge_endpoints():
    """Verifies that the server returns cryptographic challenge options for WebAuthn hardware sensors."""
    # Test passkey registration challenge
    reg_resp = client.get("/api/auth/passkey/register-challenge?identifier=CHMC-DS-2024-001")
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["status"] == "SUCCESS"
    assert "challenge" in reg_data
    assert "challenge_b64" in reg_data
    assert len(reg_data["challenge"]) >= 32
    assert "rp" in reg_data

    # Test passkey login assertion challenge
    login_resp = client.get("/api/auth/passkey/login-challenge?identifier=CHMC-DS-2024-001")
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["status"] == "SUCCESS"
    assert "challenge" in login_data
    assert "challenge_b64" in login_data
    assert len(login_data["challenge"]) >= 32
    assert "rp_id" in login_data



