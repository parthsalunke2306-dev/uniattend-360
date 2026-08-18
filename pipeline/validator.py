"""
Attendance Stream Validator and Business Rules Engine.
Performs data quality checks, deduplication, time-window mapping, and proxy heuristic flags.
"""

from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple, Dict, Any, List
from database.models import RawAttendanceLog, TimetableSession, Student, FactAttendance


class AttendanceValidator:
    """Rules engine for validating raw swipe logs against scheduled academic sessions."""

    def __init__(self, late_threshold_minutes: int = 15, pre_class_buffer_minutes: int = 20, post_class_buffer_minutes: int = 45):
        self.late_threshold_minutes = late_threshold_minutes
        self.pre_class_buffer_minutes = pre_class_buffer_minutes
        self.post_class_buffer_minutes = post_class_buffer_minutes

    def match_log_to_session(
        self, 
        log: RawAttendanceLog, 
        sessions: List[TimetableSession]
    ) -> Optional[Tuple[TimetableSession, str, bool]]:
        """
        Matches a raw scan timestamp to the active timetable session in the specified room.
        Returns: (TimetableSession, status ['PRESENT', 'LATE'], is_late: bool) or None
        """
        scan_time = log.scan_timestamp.time()
        scan_day = log.scan_timestamp.strftime("%A")

        for sess in sessions:
            # Must match room and day of week
            if sess.room_number != log.room_code or sess.day_of_week != scan_day:
                continue

            s_time = sess.start_time
            if isinstance(s_time, str):
                s_time = datetime.strptime(s_time.split(".")[0], "%H:%M:%S").time()

            e_time = sess.end_time
            if isinstance(e_time, str):
                e_time = datetime.strptime(e_time.split(".")[0], "%H:%M:%S").time()

            # Calculate allowed window
            sess_start_dt = datetime.combine(log.scan_timestamp.date(), s_time)
            sess_end_dt = datetime.combine(log.scan_timestamp.date(), e_time)

            window_start = sess_start_dt - timedelta(minutes=self.pre_class_buffer_minutes)
            window_end = sess_start_dt + timedelta(minutes=self.post_class_buffer_minutes)

            if window_start <= log.scan_timestamp <= window_end:
                # Determine if student is on time or late
                late_cutoff = sess_start_dt + timedelta(minutes=self.late_threshold_minutes)
                if log.scan_timestamp <= late_cutoff:
                    return sess, "PRESENT", False
                else:
                    return sess, "LATE", True

        return None

    @staticmethod
    def detect_instant_duplicates(logs: List[RawAttendanceLog], window_seconds: int = 60) -> List[int]:
        """
        Identifies duplicate scans by the same student within a short time window.
        Returns list of log IDs to be marked as REJECTED_DUPLICATE.
        """
        duplicate_ids = []
        # Sort logs by student_id_str and timestamp
        sorted_logs = sorted(logs, key=lambda x: (x.student_id_str, x.scan_timestamp))

        for i in range(1, len(sorted_logs)):
            prev_log = sorted_logs[i - 1]
            curr_log = sorted_logs[i]

            if curr_log.student_id_str == prev_log.student_id_str:
                time_diff = (curr_log.scan_timestamp - prev_log.scan_timestamp).total_seconds()
                if time_diff <= window_seconds:
                    duplicate_ids.append(curr_log.id)

        return duplicate_ids
