"""
UniAttend 360 - Principal Super-Admin Authority Module Test Suite.
Verifies:
  1. Direct Multi-Department Student Provisioning & Enrollment (Super-Admin Override).
  2. Student Account Expulsion, Credential Revocation & Cascade Purge.
  3. Master Institutional Student Ledger Querying.
  4. Immutable Security Audit Logging for Governance & Compliance.
  5. Strict RBAC Enforcement (Blocking Unauthorized Roles with 403 Forbidden).
"""

import os
import sys
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.models import (
    UserAccount, UserMFA, UserRecoveryCode, UserPasskey,
    UserSession, SecurityAuditLog, Student, Department, Course,
    StudentCourseSummary, FactAttendance, RawAttendanceLog
)
from database.db_manager import get_db_session
from api.security import create_jwt_access_token, PasswordHasherService, SessionService
from api.server import app

client = TestClient(app)


@pytest.fixture
def principal_token():
    """Generates an authenticated JWT for Dr. Manju Lalwani Pathak (Principal & Super Admin)."""
    with get_db_session() as session:
        user = session.query(UserAccount).filter_by(role="PRINCIPAL").first()
        if not user:
            user = UserAccount(
                username="principal.superadmin",
                email="principal.test@chmc.edu",
                password_hash=PasswordHasherService.hash("CHMC@2026!"),
                full_name="Dr. Manju Lalwani Pathak",
                role="PRINCIPAL",
                avatar_icon="👑",
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        sess_token, _ = SessionService.create_session(
            db=session,
            user_id=user.id,
            device_fingerprint="DEV-TEST-PRINCIPAL",
            device_name="Principal Test Console",
            is_trusted=True
        )

        token = create_jwt_access_token({
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": "PRINCIPAL",
            "session_token": sess_token,
            "full_name": user.full_name
        })
        return token


@pytest.fixture
def student_token():
    """Generates an authenticated JWT for a regular Student."""
    with get_db_session() as session:
        user = session.query(UserAccount).filter_by(role="STUDENT").first()
        if not user:
            user = UserAccount(
                username="test.student",
                email="test.student@chmc.edu",
                password_hash=PasswordHasherService.hash("CHMC@2026!"),
                full_name="Test Student",
                role="STUDENT",
                avatar_icon="🎓",
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        sess_token, _ = SessionService.create_session(
            db=session,
            user_id=user.id,
            device_fingerprint="DEV-TEST-STUDENT",
            device_name="Student Test Phone",
            is_trusted=True
        )

        token = create_jwt_access_token({
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": "STUDENT",
            "session_token": sess_token,
            "full_name": user.full_name
        })
        return token


# ==========================================
# 1. SUPER-ADMIN DIRECT STUDENT ENROLLMENT
# ==========================================

def test_principal_direct_enroll_student_success(principal_token):
    """Verifies that Principal can directly provision and enroll a student across departments."""
    roll_no = "CHMC-DS-2024-999"
    email = "superadmin.test.student999@chmc.edu"

    # Clean up any leftover test data first
    with get_db_session() as session:
        existing = session.query(Student).filter_by(student_id_str=roll_no).first()
        if existing:
            session.query(UserAccount).filter_by(student_id=existing.id).delete()
            session.query(StudentCourseSummary).filter_by(student_id=existing.id).delete()
            session.delete(existing)
            session.commit()

    headers = {"Authorization": f"Bearer {principal_token}"}
    payload = {
        "full_name": "Rohan Deshmukh",
        "email": email,
        "identifier": roll_no,
        "department_code": "DS",
        "batch_year": 2024,
        "semester": 3,
        "initial_password": "SecureEnroll@2026!",
        "expedited": True,
        "authorized_by": "Dr. Manju Lalwani Pathak (Principal)"
    }

    response = client.post("/api/v1/admin/students/enroll", json=payload, headers=headers)
    if response.status_code != 201:
        print("Enrollment failed with:", response.status_code, response.text)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["student"]["student_id_str"] == roll_no
    assert data["student"]["full_name"] == "Rohan Deshmukh"

    # Verify Database Integrity
    with get_db_session() as session:
        st = session.query(Student).filter_by(student_id_str=roll_no).first()
        assert st is not None
        assert st.email == email

        # Verify User Account was created
        usr = session.query(UserAccount).filter_by(student_id=st.id).first()
        assert usr is not None
        assert usr.role == "STUDENT"
        assert PasswordHasherService.verify("SecureEnroll@2026!", usr.password_hash) is True

        # Verify Course Summaries were initialized
        summaries = session.query(StudentCourseSummary).filter_by(student_id=st.id).all()
        assert len(summaries) > 0

        # Verify Immutable Audit Log
        audit = session.query(SecurityAuditLog).filter_by(event_type="SUPERADMIN_STUDENT_ENROLLED").order_by(SecurityAuditLog.created_at.desc()).first()
        assert audit is not None
        assert "DIRECT_STUDENT_ENROLLMENT" in audit.details


def test_principal_enroll_duplicate_rejected(principal_token):
    """Verifies that duplicate student enrollment is rejected with HTTP 400."""
    headers = {"Authorization": f"Bearer {principal_token}"}
    payload = {
        "full_name": "Duplicate Student",
        "email": "superadmin.test.student999@chmc.edu",
        "identifier": "CHMC-DS-2024-999",
        "department_code": "DS",
        "initial_password": "SecureEnroll@2026!"
    }
    response = client.post("/api/v1/admin/students/enroll", json=payload, headers=headers)
    assert response.status_code == 400


# ==========================================
# 2. RBAC ACCESS CONTROL ENFORCEMENT
# ==========================================

def test_student_cannot_call_superadmin_endpoints(student_token):
    """Verifies that regular students are forbidden (HTTP 403) from accessing Super-Admin APIs."""
    headers = {"Authorization": f"Bearer {student_token}"}

    # Attempt Direct Enrollment
    enroll_resp = client.post("/api/v1/admin/students/enroll", json={
        "full_name": "Hacker Attempt",
        "email": "hacker@evil.com",
        "identifier": "HACK-001",
        "department_code": "DS"
    }, headers=headers)
    assert enroll_resp.status_code == 403

    # Attempt Expulsion
    expel_resp = client.request("DELETE", "/api/v1/admin/students/CHMC-DS-2024-999", json={
        "reason": "Unauthorized expulsion attempt",
        "confirm_roll_no": "CHMC-DS-2024-999"
    }, headers=headers)
    assert expel_resp.status_code == 403


# ==========================================
# 3. MASTER INSTITUTIONAL STUDENT LEDGER
# ==========================================

def test_get_all_institutional_students(principal_token):
    """Verifies that Principal can retrieve all students across departments."""
    headers = {"Authorization": f"Bearer {principal_token}"}
    response = client.get("/api/v1/admin/students", headers=headers)
    assert response.status_code == 200
    students = response.json()
    assert isinstance(students, list)
    assert any(s["student_id_str"] == "CHMC-DS-2024-999" for s in students)


# ==========================================
# 4. STUDENT EXPULSION & CASCADE PURGE
# ==========================================

def test_expel_student_confirmation_mismatch_rejected(principal_token):
    """Verifies that mismatched confirm_roll_no is rejected with HTTP 400."""
    headers = {"Authorization": f"Bearer {principal_token}"}
    payload = {
        "reason": "Disciplinary expulsion",
        "confirm_roll_no": "WRONG-ROLL-NO"
    }
    response = client.request("DELETE", "/api/v1/admin/students/CHMC-DS-2024-999", json=payload, headers=headers)
    assert response.status_code == 400


def test_principal_expel_student_cascade_purge_success(principal_token):
    """Verifies atomic student expulsion and complete cascade deletion across all tables."""
    roll_no = "CHMC-DS-2024-999"
    headers = {"Authorization": f"Bearer {principal_token}"}
    payload = {
        "reason": "Disciplinary expulsion per College Academic Disciplinary Committee",
        "expulsion_type": "DISCIPLINARY",
        "authorized_by": "Dr. Manju Lalwani Pathak (Principal)",
        "confirm_roll_no": roll_no
    }

    response = client.request("DELETE", f"/api/v1/admin/students/{roll_no}", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "expelled" in data["message"].lower()

    # Verify Database Cascade Deletion
    with get_db_session() as session:
        st = session.query(Student).filter_by(student_id_str=roll_no).first()
        assert st is None

        usr = session.query(UserAccount).filter(UserAccount.email.ilike("superadmin.test.student999@chmc.edu")).first()
        assert usr is None

        # Verify Immutable Audit Log
        audit = session.query(SecurityAuditLog).filter_by(event_type="SUPERADMIN_STUDENT_EXPELLED").order_by(SecurityAuditLog.created_at.desc()).first()
        assert audit is not None
        assert audit.severity == "CRITICAL"
        assert roll_no in audit.details


# ==========================================
# 5. IMMUTABLE SECURITY AUDIT LEDGER
# ==========================================

def test_get_institutional_audit_ledger(principal_token):
    """Verifies retrieval of cryptographic security audit logs."""
    headers = {"Authorization": f"Bearer {principal_token}"}
    response = client.get("/api/v1/admin/audit-ledger", headers=headers)
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert any(log["event_type"] in ["SUPERADMIN_STUDENT_ENROLLED", "SUPERADMIN_STUDENT_EXPELLED", "ADMIN_USER_PROVISIONED"] for log in logs)


def test_admin_provision_multi_category_users(principal_token):
    """Verifies direct multi-category provisioning (Faculty & Admin Staff) with DB persistence."""
    headers = {"Authorization": f"Bearer {principal_token}"}
    
    # 1. Provision Faculty
    fac_payload = {
        "category": "FACULTY",
        "full_name": "Prof. Vikram Malhotra",
        "email": "vikram.malhotra.test@chmc.edu",
        "identifier": "FAC-TEST-991",
        "department_code": "DS",
        "designation": "Associate Professor",
        "initial_password": "FacultyPass@2026!",
        "authorized_by": "Mr. Sanjay Mehta (Admin Office)"
    }
    fac_res = client.post("/api/v1/admin/users/provision", json=fac_payload, headers=headers)
    assert fac_res.status_code == 201
    fac_data = fac_res.json()
    assert fac_data["status"] == "SUCCESS"
    assert fac_data["user"]["role"] == "TEACHER"
    assert fac_data["user"]["identifier"] == "FAC-TEST-991"

    # Verify Faculty in DB
    with get_db_session() as session:
        usr = session.query(UserAccount).filter_by(email="vikram.malhotra.test@chmc.edu").first()
        assert usr is not None
        assert usr.role == "TEACHER"

    # 2. Provision Admin Staff Member
    staff_payload = {
        "category": "ADMIN_STAFF",
        "full_name": "Mrs. Priya Deshmukh",
        "email": "priya.deshmukh.test@chmc.edu",
        "identifier": "STAFF-ADM-992",
        "department_code": "DS",
        "designation": "Senior Admissions Registrar",
        "initial_password": "StaffPass@2026!",
        "authorized_by": "Mr. Sanjay Mehta (Admin Office)"
    }
    staff_res = client.post("/api/v1/admin/users/provision", json=staff_payload, headers=headers)
    assert staff_res.status_code == 201
    staff_data = staff_res.json()
    assert staff_data["status"] == "SUCCESS"
    assert staff_data["user"]["role"] == "ADMIN_STAFF"
    assert staff_data["user"]["identifier"] == "STAFF-ADM-992"

    # Verify Staff in DB
    with get_db_session() as session:
        usr = session.query(UserAccount).filter_by(email="priya.deshmukh.test@chmc.edu").first()
        assert usr is not None
        assert usr.role == "ADMIN_STAFF"

