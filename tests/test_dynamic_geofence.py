"""
Unit and Integration Tests for Dynamic Faculty-Centric Geofencing and Real-Time Proxy Logging.
Tests:
  1. Setting and updating dynamic faculty device anchor coordinates.
  2. Haversine distance calculation to dynamic faculty anchor.
  3. Legitimate student check-in within configured perimeter (d <= R).
  4. Out-of-perimeter check-in rejection (d > R) with GEOFENCE_BREACH_OUT_OF_RANGE.
  5. Real-time proxy attempt incident logging.
  6. Dynamic perimeter threshold scaling (e.g. 10m to 50m).
  7. Incident retrieval and instructor acknowledgment.
"""

import pytest
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.anti_proxy_engine import AntiProxyEngine
from pipeline.lecture_manager import LectureManager
from api.schemas import StudentCheckInRequest, UpdateFacultyAnchorRequest
from api.server import verify_student_checkin, update_faculty_geofence_anchor, get_session_proxy_attempts, acknowledge_proxy_attempt


@pytest.fixture
def engine():
    return AntiProxyEngine(token_ttl_seconds=8)


def test_set_and_get_faculty_anchor(engine):
    """Verifies dynamic faculty device GPS coordinates can be established."""
    session_id = "LEC-TEST-GEOFENCE-001"
    anchor = engine.set_faculty_anchor(
        session_id=session_id,
        lat=19.22170,
        lon=73.16460,
        accuracy_m=2.8,
        radius_m=20.0,
        anchor_source="DEVICE_GPS"
    )

    assert anchor["session_id"] == session_id
    assert anchor["lat"] == 19.22170
    assert anchor["lon"] == 73.16460
    assert anchor["accuracy_m"] == 2.8
    assert anchor["radius_m"] == 20.0

    retrieved = engine.get_faculty_anchor(session_id)
    assert retrieved["lat"] == 19.22170
    assert retrieved["radius_m"] == 20.0


def test_in_range_checkin_with_dynamic_anchor(engine):
    """Verifies student within dynamic faculty perimeter is verified present."""
    session_id = "LEC-TEST-GEOFENCE-002"
    # Faculty laptop GPS at E-104 classroom center
    engine.set_faculty_anchor(
        session_id=session_id,
        lat=19.221700,
        lon=73.164600,
        radius_m=25.0
    )

    tok_data = engine.generate_active_token(session_id=session_id, room_code="E-104")

    # Student sitting 7 meters away inside classroom
    student_lat = 19.221750
    student_lon = 73.164630

    res = engine.verify_student_checkin(
        session_id=session_id,
        student_id_str="CHMC-DS-2024-002",
        student_name="Aarav Sharma",
        input_token_or_pin=tok_data["rolling_pin"],
        student_lat=student_lat,
        student_lon=student_lon,
        device_fingerprint="DEVICE-AARAV-001",
        room_code="E-104"
    )

    assert res["is_success"] is True
    assert res["status"] == "VERIFIED_PRESENT"
    assert res["distance_meters"] <= 25.0
    assert res["is_proxy_blocked"] is False


def test_out_of_range_proxy_attempt_logged(engine):
    """Verifies student outside perimeter is rejected and logged as proxy breach."""
    session_id = "LEC-TEST-GEOFENCE-003"
    engine.set_faculty_anchor(
        session_id=session_id,
        lat=19.221700,
        lon=73.164600,
        radius_m=15.0
    )

    tok_data = engine.generate_active_token(session_id=session_id, room_code="E-104")

    # Student attempting proxy from hostel / canteen (1.8 km away)
    remote_lat = 19.235000
    remote_lon = 73.170000

    res = engine.verify_student_checkin(
        session_id=session_id,
        student_id_str="CHMC-DS-2024-003",
        student_name="Priya Patel",
        input_token_or_pin=tok_data["rolling_pin"],
        student_lat=remote_lat,
        student_lon=remote_lon,
        device_fingerprint="DEVICE-PRIYA-REMOTE",
        room_code="E-104"
    )

    assert res["is_success"] is False
    assert res["is_proxy_blocked"] is True
    assert res["attack_type"] == "REMOTE_WHATSAPP_PROXY"
    assert res["distance_meters"] > 1000.0  # Over 1 km away
    assert "incident_id" in res

    # Verify incident was recorded in proxy logs
    incidents = engine.get_proxy_attempts(session_id)
    assert len(incidents) >= 1
    latest = incidents[0]
    assert latest["student_id_str"] == "CHMC-DS-2024-003"
    assert latest["attack_type"] == "REMOTE_WHATSAPP_PROXY"
    assert latest["is_acknowledged"] is False

    # Acknowledge incident
    ack_res = engine.acknowledge_proxy_attempt(latest["id"])
    assert ack_res is True
    assert latest["is_acknowledged"] is True


def test_dynamic_perimeter_threshold_expansion(engine):
    """Verifies expanding perimeter radius dynamically admits students previously outside."""
    session_id = "LEC-TEST-GEOFENCE-004"
    tok_data = engine.generate_active_token(session_id=session_id, room_code="E-104")

    # Student sitting 30 meters away (e.g. in large auditorium)
    faculty_lat = 19.221700
    faculty_lon = 73.164600
    student_lat = 19.221970
    student_lon = 73.164600

    # 1. Initial 10m threshold -> Rejected
    engine.set_faculty_anchor(session_id=session_id, lat=faculty_lat, lon=faculty_lon, radius_m=10.0)
    res_tight = engine.verify_student_checkin(
        session_id=session_id,
        student_id_str="CHMC-DS-2024-004",
        student_name="Rohan Gupta",
        input_token_or_pin=tok_data["rolling_pin"],
        student_lat=student_lat,
        student_lon=student_lon,
        device_fingerprint="DEVICE-ROHAN-001",
        room_code="E-104"
    )
    assert res_tight["is_success"] is False
    assert res_tight["attack_type"] == "REMOTE_WHATSAPP_PROXY"

    # 2. Expand threshold to 40m -> Accepted
    engine.set_faculty_anchor(session_id=session_id, lat=faculty_lat, lon=faculty_lon, radius_m=40.0)
    res_wide = engine.verify_student_checkin(
        session_id=session_id,
        student_id_str="CHMC-DS-2024-004",
        student_name="Rohan Gupta",
        input_token_or_pin=tok_data["rolling_pin"],
        student_lat=student_lat,
        student_lon=student_lon,
        device_fingerprint="DEVICE-ROHAN-001",
        room_code="E-104"
    )
    assert res_wide["is_success"] is True
    assert res_wide["status"] == "VERIFIED_PRESENT"


def test_api_dynamic_anchor_and_proxy_incident_pipeline():
    """End-to-end API test for dynamic anchor update and proxy attempt logging."""
    from pipeline.lecture_manager import lecture_manager
    lec = lecture_manager.create_lecture(
        faculty_name="Miss Razia Khan",
        course_name="Data Mining (Theory)",
        course_code="DS201-GEO",
        room_code="E-104",
        scheduled_date_str="2026-08-23",
        start_time="09:00 AM",
        end_time="10:00 AM",
        lecture_index=3,
        total_allotted_lectures=30
    )
    lec_id = lec["id"]
    lecture_manager.start_attendance(lec_id)

    # 1. Faculty device posts dynamic anchor via REST API
    req_anchor = UpdateFacultyAnchorRequest(
        session_id=lec_id,
        faculty_lat=19.221700,
        faculty_lon=73.164600,
        accuracy_m=3.1,
        radius_m=20.0,
        anchor_source="DEVICE_GPS"
    )
    update_res = update_faculty_geofence_anchor(req_anchor)
    assert update_res["status"] == "ANCHOR_UPDATED"

    # 2. Remote student submits proxy check-in
    req_checkin = StudentCheckInRequest(
        session_id=lec_id,
        student_id_str="CHMC-DS-2024-005",
        student_name="Ananya Verma",
        input_token_or_pin="582914",
        student_lat=19.250000,
        student_lon=73.180000,
        device_fingerprint="DEVICE-ANANYA-REMOTE",
        room_code="E-104"
    )
    verify_res = verify_student_checkin(req_checkin)
    assert verify_res["is_success"] is False
    assert verify_res["is_proxy_blocked"] is True
    assert verify_res["attack_type"] == "REMOTE_WHATSAPP_PROXY"

    # 3. Faculty retrieves session proxy attempts
    attempts = get_session_proxy_attempts(lec_id)
    assert len(attempts) >= 1
    latest_incident_id = attempts[0]["id"]

    # 4. Faculty acknowledges incident
    ack = acknowledge_proxy_attempt(latest_incident_id)
    assert ack["status"] == "ACKNOWLEDGED"
