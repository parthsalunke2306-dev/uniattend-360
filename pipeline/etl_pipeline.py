"""
ELT Ingestion & Transformation Engine for UniAttend Analytics.
Implements Medallion Architecture:
  1. Bronze -> Silver: Cleans, deduplicates, and links raw logs to academic sessions.
  2. Silver -> Gold: Generates dimensional aggregations, defaulter analytics, and risk KPI metrics.
"""

import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Set, Tuple, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from database.models import (
    RawAttendanceLog, FactAttendance, StudentCourseSummary, 
    Student, Course, TimetableSession, Department
)
from database.db_manager import get_db_session
from pipeline.validator import AttendanceValidator


class AttendanceETLPipeline:
    """End-to-End ELT Pipeline for Academic Attendance Analytics."""

    def __init__(self):
        self.validator = AttendanceValidator()

    def process_bronze_to_silver(self, session: Session) -> Dict[str, int]:
        """
        Extracts pending raw IoT/RFID scan logs, cleans & deduplicates,
        and loads into the Silver FactAttendance table.
        Also resolves ABSENT statuses for scheduled students who didn't scan.
        """
        print("[ETL Pipeline] Starting Bronze -> Silver transformation...")

        # 1. Fetch pending logs
        pending_logs: List[RawAttendanceLog] = session.query(RawAttendanceLog).filter_by(
            processing_status="PENDING"
        ).order_by(RawAttendanceLog.scan_timestamp.asc()).all()

        if not pending_logs:
            print("[ETL Pipeline] No pending raw logs found in Bronze layer.")
            return {"processed": 0, "duplicates": 0, "rejected": 0, "facts_created": 0}

        # 2. Identify and flag instant duplicates
        duplicate_ids = set(self.validator.detect_instant_duplicates(pending_logs))
        for log in pending_logs:
            if log.id in duplicate_ids:
                log.processing_status = "REJECTED_DUPLICATE"
                log.rejection_reason = "Rapid duplicate scan detected within window"

        # 3. Cache lookup dictionaries for performance
        all_sessions: List[TimetableSession] = session.query(TimetableSession).all()
        all_students: List[Student] = session.query(Student).all()
        student_by_roll = {s.student_id_str: s for s in all_students}
        course_by_id = {c.id: c for c in session.query(Course).all()}

        # Load existing facts into in-memory dictionary: (student_id, session_id, session_date) -> FactAttendance
        existing_facts: List[FactAttendance] = session.query(FactAttendance).all()
        facts_map: Dict[Tuple[int, int, date], FactAttendance] = {
            (f.student_id, f.timetable_session_id, f.session_date): f for f in existing_facts
        }

        # 4. Map valid scans to timetable sessions
        facts_created = 0
        rejected_count = 0
        valid_logs = [l for l in pending_logs if l.id not in duplicate_ids]

        # Keep track of dates and sessions that had activity
        processed_dates_sessions: Set[Tuple[date, int]] = set()

        for log in valid_logs:
            student = student_by_roll.get(log.student_id_str)
            if not student:
                log.processing_status = "REJECTED_UNKNOWN_STUDENT"
                log.rejection_reason = f"Student ID '{log.student_id_str}' not enrolled in database"
                rejected_count += 1
                continue

            match_result = self.validator.match_log_to_session(log, all_sessions)
            if not match_result:
                log.processing_status = "REJECTED_OUT_OF_WINDOW"
                log.rejection_reason = f"No active scheduled session in room {log.room_code} at {log.scan_timestamp.strftime('%H:%M')}"
                rejected_count += 1
                continue

            matched_session, status_str, is_late = match_result
            session_date = log.scan_timestamp.date()

            # Ensure student belongs to course's department
            course = course_by_id.get(matched_session.course_id)
            if student.department_id != course.department_id:
                log.processing_status = "REJECTED_WRONG_DEPARTMENT"
                log.rejection_reason = f"Student is in department {student.department_id} but course is {course.department_id}"
                rejected_count += 1
                continue

            key = (student.id, matched_session.id, session_date)

            if key in facts_map:
                existing_fact = facts_map[key]
                # If existing is ABSENT, upgrade to PRESENT or LATE
                if existing_fact.status == "ABSENT":
                    existing_fact.status = status_str
                    existing_fact.checkin_time = log.scan_timestamp
                    existing_fact.is_late = is_late
            else:
                fact = FactAttendance(
                    timetable_session_id=matched_session.id,
                    student_id=student.id,
                    course_id=matched_session.course_id,
                    session_date=session_date,
                    checkin_time=log.scan_timestamp,
                    status=status_str,
                    is_late=is_late,
                    is_proxy_suspected=False,
                    confidence_score=0.98 if not is_late else 0.85,
                    validation_notes=f"Validated via {log.scan_method} in room {log.room_code}"
                )
                session.add(fact)
                facts_map[key] = fact
                facts_created += 1

            log.processing_status = "PROCESSED"
            processed_dates_sessions.add((session_date, matched_session.id))

        # 5. Generate ABSENT records for enrolled students who missed scheduled classes
        dept_students: Dict[int, List[Student]] = {}
        for s in all_students:
            dept_students.setdefault(s.department_id, []).append(s)

        for session_date, session_id in processed_dates_sessions:
            sess_obj = next((s for s in all_sessions if s.id == session_id), None)
            if not sess_obj:
                continue

            course = course_by_id.get(sess_obj.course_id)
            enrolled = dept_students.get(course.department_id, [])

            for student in enrolled:
                key = (student.id, sess_obj.id, session_date)
                if key not in facts_map:
                    absent_fact = FactAttendance(
                        timetable_session_id=sess_obj.id,
                        student_id=student.id,
                        course_id=course.id,
                        session_date=session_date,
                        checkin_time=None,
                        status="ABSENT",
                        is_late=False,
                        is_proxy_suspected=False,
                        confidence_score=1.0,
                        validation_notes="No scan detected during scheduled lecture window"
                    )
                    session.add(absent_fact)
                    facts_map[key] = absent_fact
                    facts_created += 1

        session.commit()
        print(f"[ETL Pipeline] Bronze -> Silver complete. Created/Updated {facts_created} facts. Duplicates: {len(duplicate_ids)}, Rejected: {rejected_count}")
        return {
            "processed": len(valid_logs),
            "duplicates": len(duplicate_ids),
            "rejected": rejected_count,
            "facts_created": facts_created
        }

    def process_silver_to_gold(self, session: Session) -> int:
        """
        Aggregates Silver Fact records into Gold Summary Marts (gold_student_course_summary).
        Calculates:
          - Total held, attended, late, absent
          - Attendance %
          - Defaulter classification (< 75%)
          - 'Classes needed for 75%' & 'Can afford to miss'
        """
        print("[ETL Pipeline] Starting Silver -> Gold summary aggregation...")

        # Group fact attendance by student_id and course_id
        summary_query = session.query(
            FactAttendance.student_id,
            FactAttendance.course_id,
            func.count(FactAttendance.id).label("total_classes"),
            func.sum(case((FactAttendance.status.in_(["PRESENT", "LATE"]), 1), else_=0)).label("attended_classes"),
            func.sum(case((FactAttendance.status == "LATE", 1), else_=0)).label("late_classes"),
            func.sum(case((FactAttendance.status == "ABSENT", 1), else_=0)).label("absent_classes")
        ).group_by(FactAttendance.student_id, FactAttendance.course_id).all()

        updated_count = 0

        for row in summary_query:
            student_id = row.student_id
            course_id = row.course_id
            total = row.total_classes or 0
            attended = row.attended_classes or 0
            late = row.late_classes or 0
            absent = row.absent_classes or 0

            pct = (attended / total * 100.0) if total > 0 else 0.0
            is_defaulter = pct < 75.0

            # Calculate classes needed or can afford to miss
            # Target = 75% -> (Attended + N) / (Total + N) >= 0.75 => N >= 3*Total - 4*Attended
            if is_defaulter:
                needed = max(0, math.ceil(3 * total - 4 * attended))
                can_miss = 0
            else:
                needed = 0
                can_miss = max(0, math.floor((4 * attended - 3 * total) / 3))

            # Determine Risk Category
            if pct < 65.0:
                risk_cat = "CRITICAL"
                risk_score = 90.0 + (65.0 - pct)
            elif pct < 75.0:
                risk_cat = "WARNING"
                risk_score = 60.0 + (75.0 - pct) * 3.0
            else:
                risk_cat = "SAFE"
                risk_score = max(0.0, 50.0 - (pct - 75.0) * 2.0)

            # Update or create summary record
            summary_record = session.query(StudentCourseSummary).filter_by(
                student_id=student_id,
                course_id=course_id
            ).first()

            if not summary_record:
                summary_record = StudentCourseSummary(
                    student_id=student_id,
                    course_id=course_id,
                    total_classes=total,
                    attended_classes=attended,
                    late_classes=late,
                    absent_classes=absent,
                    attendance_pct=round(pct, 2),
                    is_defaulter=is_defaulter,
                    classes_needed_for_75=needed,
                    can_afford_to_miss=can_miss,
                    risk_score=round(min(100.0, risk_score), 2),
                    risk_category=risk_cat,
                    last_updated=datetime.now()
                )
                session.add(summary_record)
            else:
                summary_record.total_classes = total
                summary_record.attended_classes = attended
                summary_record.late_classes = late
                summary_record.absent_classes = absent
                summary_record.attendance_pct = round(pct, 2)
                summary_record.is_defaulter = is_defaulter
                summary_record.classes_needed_for_75 = needed
                summary_record.can_afford_to_miss = can_miss
                summary_record.risk_score = round(min(100.0, risk_score), 2)
                summary_record.risk_category = risk_cat
                summary_record.last_updated = datetime.now()

            updated_count += 1

        session.commit()
        print(f"[ETL Pipeline] Silver -> Gold complete. Updated {updated_count} student-course summary records.")
        return updated_count

    def run_pipeline(self) -> Dict[str, Any]:
        """Executes full Bronze -> Silver -> Gold ELT run."""
        with get_db_session() as session:
            silver_metrics = self.process_bronze_to_silver(session)
            gold_count = self.process_silver_to_gold(session)
            return {
                "silver_metrics": silver_metrics,
                "gold_summaries_updated": gold_count
            }


if __name__ == "__main__":
    pipeline = AttendanceETLPipeline()
    results = pipeline.run_pipeline()
    print(f"[ETL Main] Finished pipeline execution: {results}")
