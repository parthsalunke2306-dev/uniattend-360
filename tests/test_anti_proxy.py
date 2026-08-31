"""
Unit & Security Attack Simulation Tests for the Anti-Proxy Engine.
Tests:
  1. Valid in-class student check-in.
  2. Attack 1: Remote WhatsApp QR photo scan (fails GPS Geofence).
  3. Attack 2: Device sharing / logging into absent friend's account in class (fails Device Lock).
  4. Attack 3: Expired / Stale QR Token (fails Time-to-Live).
"""

import pytest
import time
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.anti_proxy_engine import AntiProxyEngine, DEFAULT_CLASSROOM_GEO


@pytest.fixture
def engine():
    return AntiProxyEngine(token_ttl_seconds=5)


def test_token_and_qr_generation(engine):
    """Verifies HMAC token and rolling 6-digit PIN generation."""
    token_data = engine.generate_active_token(session_id="SESS-101", room_code="LH-101")
    assert "token" in token_data
    assert "rolling_pin" in token_data
    assert len(token_data["rolling_pin"]) == 6
    assert token_data["rolling_pin"].isdigit()

    # Generate QR Base64
    qr_b64 = engine.generate_qr_image_base64(token_data)
    assert len(qr_b64) > 100


def test_manual_6digit_pin_verification_success(engine):
    """Verifies student manual submission of active 6-digit PIN."""
    class_geo = DEFAULT_CLASSROOM_GEO["LH-101"]
    token_data = engine.generate_active_token(session_id="SESS-101", room_code="LH-101")
    pin = token_data["rolling_pin"]

    result = engine.verify_student_checkin(
        session_id="SESS-101",
        student_id_str="CSE-2024-001",
        student_name="Alex Chen",
        input_token_or_pin=pin,
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-PHONE-ALPHA-99",
        room_code="LH-101"
    )

    assert result["is_success"] is True
    assert result["status"] == "VERIFIED_PRESENT"


def test_manual_6digit_pin_drift_tolerance(engine):
    """Verifies student submission of 6-digit PIN from previous 5s cycle (T-1) succeeds."""
    class_geo = DEFAULT_CLASSROOM_GEO["LH-101"]
    now = time.time()
    prev_time = now - 4.0  # Previous 5s window
    prev_token_data = engine.generate_active_token(session_id="SESS-101", room_code="LH-101", custom_time=prev_time)
    prev_pin = prev_token_data["rolling_pin"]

    result = engine.verify_student_checkin(
        session_id="SESS-101",
        student_id_str="CSE-2024-001",
        student_name="Alex Chen",
        input_token_or_pin=prev_pin,
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-PHONE-ALPHA-99",
        room_code="LH-101",
        custom_time=now + 1.0
    )

    assert result["is_success"] is True
    assert result["status"] == "VERIFIED_PRESENT"


def test_manual_6digit_pin_invalid_rejected(engine):
    """Verifies invalid or guessed 6-digit PIN is strictly rejected."""
    class_geo = DEFAULT_CLASSROOM_GEO["LH-101"]
    
    result = engine.verify_student_checkin(
        session_id="SESS-101",
        student_id_str="CSE-2024-001",
        student_name="Alex Chen",
        input_token_or_pin="000000",  # Fake PIN
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-PHONE-ALPHA-99",
        room_code="LH-101"
    )

    assert result["is_success"] is False
    assert result["status"] == "PROXY_ATTEMPT_BLOCKED"
    assert result["shields"]["token_valid"] is False


def test_legitimate_in_class_checkin(engine):
    """Scenario: Student physically in LH-101 scans active QR."""
    class_geo = DEFAULT_CLASSROOM_GEO["LH-101"]
    token_data = engine.generate_active_token(session_id="SESS-101", room_code="LH-101")

    # Student coordinates 10 meters away from lecturer desk
    student_lat = class_geo["lat"] + 0.00005
    student_lon = class_geo["lon"] + 0.00005

    result = engine.verify_student_checkin(
        session_id="SESS-101",
        student_id_str="CSE-2024-001",
        student_name="Alex Chen",
        input_token_or_pin=token_data["token"],
        student_lat=student_lat,
        student_lon=student_lon,
        device_fingerprint="DEVICE-PHONE-ALPHA-99",
        room_code="LH-101"
    )

    assert result["is_success"] is True
    assert result["status"] == "VERIFIED_PRESENT"
    assert result["distance_meters"] <= 50.0


def test_attack_remote_whatsapp_qr_blocked(engine):
    """Scenario: Absent student at home scans forwarded QR photo (GPS 1.8km away)."""
    token_data = engine.generate_active_token(session_id="SESS-101", room_code="LH-101")

    # Student is at home (approx 1.8 km away)
    home_lat = 28.56000
    home_lon = 77.20000

    result = engine.verify_student_checkin(
        session_id="SESS-101",
        student_id_str="CSE-2024-002",
        student_name="Brian Fox (Absent at Home)",
        input_token_or_pin=token_data["token"],
        student_lat=home_lat,
        student_lon=home_lon,
        device_fingerprint="DEVICE-HOME-PHONE-22",
        room_code="LH-101"
    )

    assert result["is_success"] is False
    assert result["status"] == "PROXY_ATTEMPT_BLOCKED"
    assert result["attack_type"] == "REMOTE_WHATSAPP_PROXY"
    assert result["shields"]["geo_valid"] is False


def test_attack_device_sharing_in_class_blocked(engine):
    """Scenario: Student in class marks for himself, then tries to mark for absent friend on same phone."""
    class_geo = DEFAULT_CLASSROOM_GEO["LH-101"]
    token_data = engine.generate_active_token(session_id="SESS-101", room_code="LH-101")

    student_lat = class_geo["lat"]
    student_lon = class_geo["lon"]
    shared_device = "DEVICE-SAME-IPHONE-777"

    # 1. First student marks legitimately
    res1 = engine.verify_student_checkin(
        session_id="SESS-101",
        student_id_str="CSE-2024-001",
        student_name="Alex Chen",
        input_token_or_pin=token_data["token"],
        student_lat=student_lat,
        student_lon=student_lon,
        device_fingerprint=shared_device,
        room_code="LH-101"
    )
    assert res1["is_success"] is True

    # 2. Same phone tries to mark for friend 'David Miller'
    res2 = engine.verify_student_checkin(
        session_id="SESS-101",
        student_id_str="CSE-2024-002",
        student_name="David Miller (Proxy Attempt)",
        input_token_or_pin=token_data["token"],
        student_lat=student_lat,
        student_lon=student_lon,
        device_fingerprint=shared_device,
        room_code="LH-101"
    )
    assert res2["is_success"] is False
    assert res2["status"] == "PROXY_ATTEMPT_BLOCKED"
    assert res2["attack_type"] == "DEVICE_SHARING_PROXY"
    assert res2["shields"]["device_valid"] is False


def test_attack_expired_token_blocked(engine):
    """Scenario: Token from 60 seconds ago is scanned."""
    class_geo = DEFAULT_CLASSROOM_GEO["LH-101"]
    old_time = time.time() - 60.0
    stale_token_data = engine.generate_active_token(session_id="SESS-101", room_code="LH-101", custom_time=old_time)

    result = engine.verify_student_checkin(
        session_id="SESS-101",
        student_id_str="CSE-2024-003",
        student_name="Chloe Adams",
        input_token_or_pin=stale_token_data["token"],
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-CHLOE-88",
        room_code="LH-101"
    )

    assert result["is_success"] is False
    assert result["status"] == "PROXY_ATTEMPT_BLOCKED"
    assert result["shields"]["token_valid"] is False
