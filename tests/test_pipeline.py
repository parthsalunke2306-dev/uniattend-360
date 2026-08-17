"""
Unit & Integration Tests for Ingestion, Deduplication, and ELT Pipeline.
"""

import pytest
import os
import sys
from datetime import datetime, date, time, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.models import (
    University, College, Department, Course, Student, TimetableSession, 
    RawAttendanceLog, FactAttendance, StudentCourseSummary
)
from database.db_manager import get_db_session, init_db
from pipeline.validator import AttendanceValidator
from pipeline.etl_pipeline import AttendanceETLPipeline
from data.data_generator import seed_hierarchy_and_academics, generate_raw_attendance_stream


@pytest.fixture(scope="module")
def setup_database():
    """Initializes schema and seeds initial data."""
    init_db()
    with get_db_session() as session:
        seed_hierarchy_and_academics(session)
        generate_raw_attendance_stream(session, weeks=4)
    yield


def test_validator_duplicate_detection():
    """Tests that duplicate scans within window are accurately flagged."""
    validator = AttendanceValidator()
    now = datetime.now()
    
    logs = [
        RawAttendanceLog(id=1, student_id_str="CS-01", scan_timestamp=now, room_code="LH-101"),
        RawAttendanceLog(id=2, student_id_str="CS-01", scan_timestamp=now + timedelta(seconds=15), room_code="LH-101"),
        RawAttendanceLog(id=3, student_id_str="CS-02", scan_timestamp=now, room_code="LH-101"),
    ]
    
    dup_ids = validator.detect_instant_duplicates(logs, window_seconds=30)
    assert 2 in dup_ids
    assert 1 not in dup_ids
    assert 3 not in dup_ids


def test_etl_bronze_to_silver_and_gold(setup_database):
    """Tests the full ELT execution cycle."""
    pipeline = AttendanceETLPipeline()
    results = pipeline.run_pipeline()

    assert results["silver_metrics"]["facts_created"] > 0
    assert results["gold_summaries_updated"] > 0

    with get_db_session() as session:
        summaries = session.query(StudentCourseSummary).all()
        assert len(summaries) > 0
        for s in summaries:
            assert 0.0 <= s.attendance_pct <= 100.0
            assert s.total_classes >= s.attended_classes
            if s.is_defaulter:
                assert s.attendance_pct < 75.0
                assert s.classes_needed_for_75 >= 0
            else:
                assert s.attendance_pct >= 75.0
                assert s.can_afford_to_miss >= 0
