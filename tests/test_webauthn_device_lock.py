"""
Unit & Integration Tests for WebAuthn Hardware Passkeys & Strict 1-Device-Per-Student Lock.
Verifies:
  1. Primary hardware device registration and binding.
  2. Rejection of check-ins from unauthorized secondary devices.
  3. Anti-cycling multi-account handset defense (preventing 1 phone from marking attendance for multiple students).
  4. Emergency Faculty Device Reset workflow.
  5. Full FastAPI REST endpoint integration for hardware device management.
"""

import pytest
import time
from fastapi.testclient import TestClient

from pipeline.anti_proxy_engine import AntiProxyEngine
from api.server import app


@pytest.fixture
def clean_engine():
    """Returns a fresh AntiProxyEngine instance for testing."""
    engine = AntiProxyEngine(token_ttl_seconds=8)
    # Set faculty anchor at E-104
    engine.set_faculty_anchor(
        session_id="TEST_LEC_01",
        lat=19.22170,
        lon=73.16460,
        accuracy_m=2.0,
        radius_m=10.0,
        anchor_source="DEVICE_GPS"
    )
    return engine


@pytest.fixture
def client():
    """FastAPI TestClient instance."""
    return TestClient(app)


def test_first_time_device_auto_binding(clean_engine):
    """Test that student's first legitimate check-in permanently binds their primary device."""
    token_data = clean_engine.generate_active_token(session_id="TEST_LEC_01", room_code="E-104")
    pin = token_data["rolling_pin"]

    # Student 001 checks in with Primary iPhone
    result = clean_engine.verify_student_checkin(
        session_id="TEST_LEC_01",
        student_id_str="CHMC-DS-2024-001",
        student_name="Captain Alex",
        input_token_or_pin=pin,
        student_lat=19.22170,
        student_lon=73.16460,
        device_fingerprint="DEV-IPHONE-15-PRO-001",
        room_code="E-104"
    )

    assert result["is_success"] is True
    assert result["status"] == "VERIFIED_PRESENT"

    # Verify student is now locked to this device
    status = clean_engine.get_student_device_status("CHMC-DS-2024-001")
    assert status["is_locked"] is True
    assert status["device_info"]["device_uuid"] == "DEV-IPHONE-15-PRO-001"


def test_unauthorized_device_mismatch_rejected(clean_engine):
    """Test that a student cannot check in from a friend's phone or secondary device."""
    token_data = clean_engine.generate_active_token(session_id="TEST_LEC_01", room_code="E-104")
    pin = token_data["rolling_pin"]

    # Pre-bind student 001 to their primary iPhone
    clean_engine.bind_student_device("CHMC-DS-2024-001", "DEV-IPHONE-15-PRO-001", "Alex's iPhone")

    # Student 001 tries to check in from an unauthorized Android phone
    result = clean_engine.verify_student_checkin(
        session_id="TEST_LEC_01",
        student_id_str="CHMC-DS-2024-001",
        student_name="Captain Alex",
        input_token_or_pin=pin,
        student_lat=19.22170,
        student_lon=73.16460,
        device_fingerprint="DEV-SAMSUNG-S24-UNAUTHORIZED",
        room_code="E-104"
    )

    assert result["is_success"] is False
    assert result["is_proxy_blocked"] is True
    assert result["attack_type"] == "DEVICE_MISMATCH_UNAUTHORIZED_HARDWARE"
    assert "Unauthorized Handset" in result["failure_reason"]


def test_anti_cycling_same_handset_blocked_for_multiple_students(clean_engine):
    """Test that one physical phone cannot be used to submit attendance for multiple accounts in the same lecture."""
    token_data = clean_engine.generate_active_token(session_id="TEST_LEC_01", room_code="E-104")
    pin = token_data["rolling_pin"]

    shared_device = "DEV-PHYSICAL-HANDSET-XYZ"

    # Student 001 checks in on shared_device -> SUCCESS
    res1 = clean_engine.verify_student_checkin(
        session_id="TEST_LEC_01",
        student_id_str="CHMC-DS-2024-001",
        student_name="Captain Alex",
        input_token_or_pin=pin,
        student_lat=19.22170,
        student_lon=73.16460,
        device_fingerprint=shared_device,
        room_code="E-104"
    )
    assert res1["is_success"] is True

    # Student 002 immediately tries to check in from the SAME phone in the same lecture
    res2 = clean_engine.verify_student_checkin(
        session_id="TEST_LEC_01",
        student_id_str="CHMC-DS-2024-002",
        student_name="Priya Sharma",
        input_token_or_pin=pin,
        student_lat=19.22170,
        student_lon=73.16460,
        device_fingerprint=shared_device,
        room_code="E-104"
    )

    assert res2["is_success"] is False
    assert res2["is_proxy_blocked"] is True
    assert res2["attack_type"] == "DEVICE_SHARING_PROXY"
    assert "Device Hardware Re-use Detected" in res2["failure_reason"]


def test_faculty_emergency_device_reset(clean_engine):
    """Test that faculty can reset a student's hardware lock, allowing new phone enrollment."""
    # Bind initial device
    clean_engine.bind_student_device("CHMC-DS-2024-003", "OLD-BROKEN-PHONE-001", "Old Phone")
    assert clean_engine.get_student_device_status("CHMC-DS-2024-003")["is_locked"] is True

    # Faculty performs emergency reset
    reset_res = clean_engine.reset_student_device("CHMC-DS-2024-003", authorized_by="Miss Razia Khan")
    assert reset_res["status"] == "RESET_SUCCESSFUL"
    assert reset_res["unlinked_device"]["device_uuid"] == "OLD-BROKEN-PHONE-001"

    # Status is now unlocked
    assert clean_engine.get_student_device_status("CHMC-DS-2024-003")["is_locked"] is False

    # Student now checks in with their new replacement phone -> SUCCESS
    token_data = clean_engine.generate_active_token(session_id="TEST_LEC_01", room_code="E-104")
    checkin_res = clean_engine.verify_student_checkin(
        session_id="TEST_LEC_01",
        student_id_str="CHMC-DS-2024-003",
        student_name="Rahul Varma",
        input_token_or_pin=token_data["rolling_pin"],
        student_lat=19.22170,
        student_lon=73.16460,
        device_fingerprint="NEW-UPGRADED-PHONE-002",
        room_code="E-104"
    )
    assert checkin_res["is_success"] is True
    assert clean_engine.get_student_device_status("CHMC-DS-2024-003")["device_info"]["device_uuid"] == "NEW-UPGRADED-PHONE-002"


def test_rest_api_device_endpoints(client):
    """Test REST API routes for device status, binding, and emergency reset."""
    # 1. Bind device via API
    bind_resp = client.post("/api/v1/attendance/device/bind", json={
        "student_id_str": "CHMC-DS-2024-005",
        "device_uuid": "REST-API-IPHONE-UUID-999",
        "device_name": "Apple iPhone 15 Pro Max"
    })
    assert bind_resp.status_code == 200
    assert bind_resp.json()["status"] == "DEVICE_BOUND"

    # 2. Get status via API
    status_resp = client.get("/api/v1/attendance/device/status/CHMC-DS-2024-005")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["is_locked"] is True
    assert data["device_info"]["device_uuid"] == "REST-API-IPHONE-UUID-999"

    # 3. Emergency Reset via API
    reset_resp = client.post("/api/v1/attendance/device/reset", json={
        "student_id_str": "CHMC-DS-2024-005",
        "authorized_by": "Miss Razia Khan",
        "reason": "Student phone replaced after water damage"
    })
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "RESET_SUCCESSFUL"

    # 4. Verify unlocked
    status_resp_after = client.get("/api/v1/attendance/device/status/CHMC-DS-2024-005")
    assert status_resp_after.json()["is_locked"] is False


def test_cross_device_user_status_and_first_login_setup(client):
    """Verifies that first-login setup saves to database and user-status endpoint syncs across devices."""
    roll_no = "CHMC-DS-2024-099"
    
    # Check initial status (unbound)
    init_status = client.get(f"/api/v1/auth/user-status/{roll_no}")
    assert init_status.status_code == 200
    assert init_status.json()["is_device_bound"] is False

    # Perform First-Time Setup on Mobile Handset
    setup_resp = client.post("/api/v1/auth/first-login-setup", json={
        "identifier": roll_no,
        "new_password": "PermanentSecurePass@2026!",
        "device_uuid": "MOBILE-IPHONE-ENCLAVE-UUID-777",
        "device_name": "Apple iPhone 15 Pro",
        "webauthn_credential": {
            "id": "cred_test_webauthn_123",
            "rawId": "637265645f74657374",
            "type": "public-key"
        }
    })
    assert setup_resp.status_code == 200
    data = setup_resp.json()
    assert data["status"] == "SUCCESS"
    assert data["is_device_bound"] is True
    assert data["must_change_password"] is False
    assert data["device_name"] == "Apple iPhone 15 Pro"

    # Now verify from a second client/device (e.g. Windows browser opening user-status)
    windows_query = client.get(f"/api/v1/auth/user-status/{roll_no}")
    assert windows_query.status_code == 200
    w_data = windows_query.json()
    assert w_data["is_device_bound"] is True
    assert w_data["must_change_password"] is False
    assert w_data["bound_device_name"] == "Apple iPhone 15 Pro"
    assert w_data["bound_device_uuid"] == "MOBILE-IPHONE-ENCLAVE-UUID-777"

