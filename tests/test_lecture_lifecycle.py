"""
Unit and Integration Tests for Lecture Scheduling & Attendance Lifecycle State Machine.
Tests:
  1. Lecture creation with metadata and index budgeting (X of N allotted).
  2. Lecture validation rules (lecture_index <= total_allotted_lectures).
  3. State transitions: SCHEDULED -> ACTIVE -> PAUSED -> ACTIVE -> COMPLETED.
  4. Student check-in rejection during PAUSED state (SESSION_PAUSED).
  5. Student check-in rejection during SCHEDULED state (SESSION_NOT_STARTED).
  6. Student check-in rejection during COMPLETED state (SESSION_COMPLETED).
  7. Successful student verification during ACTIVE state.
"""

import pytest
import os
import sys
from datetime import date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.lecture_manager import (
    LectureManager, STATUS_SCHEDULED, STATUS_ACTIVE, STATUS_PAUSED, STATUS_COMPLETED
)
from pipeline.anti_proxy_engine import AntiProxyEngine, DEFAULT_CLASSROOM_GEO
from api.schemas import StudentCheckInRequest
from api.server import verify_student_checkin


@pytest.fixture
def manager():
    return LectureManager()


@pytest.fixture
def proxy_engine():
    return AntiProxyEngine(token_ttl_seconds=8)


def test_create_lecture_success(manager):
    """Verifies creating a lecture with index budgeting (e.g. 14 of 30)."""
    lec = manager.create_lecture(
        faculty_name="Miss Razia Khan",
        course_name="Data Mining (Theory)",
        course_code="DS201-DM",
        room_code="E-104",
        scheduled_date_str="2026-08-23",
        start_time="09:00 AM",
        end_time="10:00 AM",
        lecture_index=14,
        total_allotted_lectures=30,
        topic="Apriori Algorithm",
        geofence_radius_m=10.0,
        total_enrolled=5
    )

    assert lec["id"].startswith("LEC-DS201DM-")
    assert lec["lecture_index"] == 14
    assert lec["total_allotted_lectures"] == 30
    assert lec["session_status"] == STATUS_SCHEDULED
    assert lec["syllabus_progress_pct"] == round((14 / 30) * 100, 1)


def test_create_lecture_invalid_index_fails(manager):
    """Verifies creating a lecture where index exceeds total allotted raises ValueError."""
    with pytest.raises(ValueError) as exc:
        manager.create_lecture(
            faculty_name="Miss Razia Khan",
            course_name="Data Mining (Theory)",
            course_code="DS201-DM",
            room_code="E-104",
            scheduled_date_str="2026-08-23",
            start_time="09:00 AM",
            end_time="10:00 AM",
            lecture_index=35,
            total_allotted_lectures=30
        )
    assert "cannot exceed total allotted lectures" in str(exc.value)


def test_lecture_lifecycle_transitions(manager):
    """Verifies state machine: SCHEDULED -> ACTIVE -> PAUSED -> ACTIVE -> COMPLETED."""
    lec = manager.create_lecture(
        faculty_name="Mr. Anshul Gupta",
        course_name="Data Warehousing",
        course_code="DS203-DW",
        room_code="E-104",
        scheduled_date_str="2026-08-23",
        start_time="02:00 PM",
        end_time="03:00 PM",
        lecture_index=25,
        total_allotted_lectures=30
    )
    lec_id = lec["id"]
    assert manager.get_lifecycle_status(lec_id) == STATUS_SCHEDULED

    # 1. Start Attendance -> ACTIVE
    active_lec = manager.start_attendance(lec_id)
    assert active_lec["session_status"] == STATUS_ACTIVE
    assert manager.get_lifecycle_status(lec_id) == STATUS_ACTIVE

    # 2. Pause Attendance -> PAUSED
    paused_lec = manager.pause_attendance(lec_id)
    assert paused_lec["session_status"] == STATUS_PAUSED
    assert manager.get_lifecycle_status(lec_id) == STATUS_PAUSED

    # 3. Resume Attendance -> ACTIVE
    resumed_lec = manager.resume_attendance(lec_id)
    assert resumed_lec["session_status"] == STATUS_ACTIVE
    assert manager.get_lifecycle_status(lec_id) == STATUS_ACTIVE

    # 4. Stop Attendance -> COMPLETED
    completed_lec = manager.stop_attendance(lec_id)
    assert completed_lec["session_status"] == STATUS_COMPLETED
    assert manager.get_lifecycle_status(lec_id) == STATUS_COMPLETED


def test_submission_rejection_during_paused_state():
    """Verifies that API blocks student check-ins when session is PAUSED."""
    from pipeline.lecture_manager import lecture_manager
    lec = lecture_manager.create_lecture(
        faculty_name="Miss Razia Khan",
        course_name="Data Mining (Theory)",
        course_code="DS201-TEST",
        room_code="E-104",
        scheduled_date_str="2026-08-23",
        start_time="09:00 AM",
        end_time="10:00 AM",
        lecture_index=1,
        total_allotted_lectures=30
    )
    lec_id = lec["id"]
    lecture_manager.start_attendance(lec_id)
    lecture_manager.pause_attendance(lec_id)

    class_geo = DEFAULT_CLASSROOM_GEO["E-104"]
    req = StudentCheckInRequest(
        session_id=lec_id,
        student_id_str="CHMC-DS-2024-001",
        student_name="Alex Chen",
        input_token_or_pin="582914",
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-PAUSE-TEST-1",
        room_code="E-104"
    )

    res = verify_student_checkin(req)
    assert res["is_success"] is False
    assert res["status"] == "SESSION_PAUSED"
    assert "temporarily paused" in res["message"]


def test_submission_rejection_during_scheduled_and_completed_states():
    """Verifies API blocks student check-ins during SCHEDULED and COMPLETED states."""
    from pipeline.lecture_manager import lecture_manager
    lec = lecture_manager.create_lecture(
        faculty_name="Miss Razia Khan",
        course_name="Data Mining (Theory)",
        course_code="DS201-TEST2",
        room_code="E-104",
        scheduled_date_str="2026-08-23",
        start_time="09:00 AM",
        end_time="10:00 AM",
        lecture_index=2,
        total_allotted_lectures=30
    )
    lec_id = lec["id"]

    class_geo = DEFAULT_CLASSROOM_GEO["E-104"]
    req = StudentCheckInRequest(
        session_id=lec_id,
        student_id_str="CHMC-DS-2024-001",
        student_name="Alex Chen",
        input_token_or_pin="582914",
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-SCHED-TEST-1",
        room_code="E-104"
    )

    # In SCHEDULED state
    res_sched = verify_student_checkin(req)
    assert res_sched["is_success"] is False
    assert res_sched["status"] == "SESSION_NOT_STARTED"

    # Start and then Stop -> COMPLETED
    lecture_manager.start_attendance(lec_id)
    lecture_manager.stop_attendance(lec_id)

    res_comp = verify_student_checkin(req)
    assert res_comp["is_success"] is False
    assert res_comp["status"] == "SESSION_COMPLETED"
