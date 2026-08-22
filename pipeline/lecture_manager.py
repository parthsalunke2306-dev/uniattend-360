"""
Lecture Session & Attendance Lifecycle State Manager.
Manages:
  1. Advance & on-the-fly Lecture Scheduling (Date, Subject, Room, Lecture Index X of N allotted).
  2. Attendance Lifecycle State Machine: SCHEDULED -> ACTIVE <-> PAUSED -> COMPLETED.
  3. Strict submission rejection during non-ACTIVE states (PAUSED, SCHEDULED, COMPLETED).
"""

import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from database.db_manager import get_db_session
from database.models import LectureSession, Faculty, Course


# Valid lifecycle status constants
STATUS_SCHEDULED = "SCHEDULED"
STATUS_ACTIVE = "ACTIVE"
STATUS_PAUSED = "PAUSED"
STATUS_COMPLETED = "COMPLETED"


class LectureManager:
    """Orchestrates lecture scheduling, lecture indexing, and live attendance state transitions."""

    def __init__(self):
        # In-memory fast cache for high-throughput live kiosk checks
        # {lecture_id: {"status": "ACTIVE", "present_count": 4, ...}}
        self._live_sessions: Dict[str, Dict[str, Any]] = {}
        self._seed_default_lectures()

    def _seed_default_lectures(self):
        """Pre-seeds default Second Year Data Science lectures for instant faculty testing."""
        default_lectures = [
            {
                "id": "LEC-DS201-20260823-14",
                "faculty_name": "Miss Razia Khan",
                "course_code": "DS201-DM",
                "course_name": "Data Mining (Theory)",
                "room_code": "E-104",
                "scheduled_date": date.today(),
                "start_time": "09:00 AM",
                "end_time": "10:00 AM",
                "lecture_index": 14,
                "total_allotted_lectures": 30,
                "topic": "Frequent Itemset Mining & Apriori Algorithm",
                "session_status": STATUS_ACTIVE,
                "present_count": 4,
                "total_enrolled": 5,
                "geofence_radius_m": 10.0,
                "started_at": datetime.now()
            },
            {
                "id": "LEC-DS202-20260823-12",
                "faculty_name": "Miss Razia Khan",
                "course_code": "DS202-DMLAB",
                "course_name": "Data Mining (Lab)",
                "room_code": "M-113",
                "scheduled_date": date.today(),
                "start_time": "11:00 AM",
                "end_time": "01:00 PM",
                "lecture_index": 12,
                "total_allotted_lectures": 15,
                "topic": "Hands-on WEKA Classification & Clustering",
                "session_status": STATUS_SCHEDULED,
                "present_count": 0,
                "total_enrolled": 5,
                "geofence_radius_m": 10.0
            },
            {
                "id": "LEC-DS203-20260824-25",
                "faculty_name": "Mr. Anshul Gupta",
                "course_code": "DS203-DW",
                "course_name": "Data Warehousing",
                "room_code": "E-104",
                "scheduled_date": date.today(),
                "start_time": "02:00 PM",
                "end_time": "03:00 PM",
                "lecture_index": 25,
                "total_allotted_lectures": 30,
                "topic": "Star vs Snowflake Schemas in ETL",
                "session_status": STATUS_SCHEDULED,
                "present_count": 0,
                "total_enrolled": 5,
                "geofence_radius_m": 10.0
            },
            {
                "id": "LEC-DS204-20260824-12",
                "faculty_name": "Mr. Anshul Gupta",
                "course_code": "DS204-FORLAB",
                "course_name": "FOR Lab",
                "room_code": "M-103",
                "scheduled_date": date.today(),
                "start_time": "03:00 PM",
                "end_time": "05:00 PM",
                "lecture_index": 12,
                "total_allotted_lectures": 15,
                "topic": "Simplex Method Optimization in Python",
                "session_status": STATUS_SCHEDULED,
                "present_count": 0,
                "total_enrolled": 5,
                "geofence_radius_m": 10.0
            }
        ]

        for item in default_lectures:
            self._live_sessions[item["id"]] = item.copy()

    # ----------------------------------------------------
    # 1. LECTURE CREATION & RETRIEVAL
    # ----------------------------------------------------

    def create_lecture(
        self,
        faculty_name: str,
        course_name: str,
        course_code: str,
        room_code: str,
        scheduled_date_str: str,
        start_time: str,
        end_time: str,
        lecture_index: int,
        total_allotted_lectures: int,
        topic: Optional[str] = None,
        geofence_radius_m: float = 10.0,
        total_enrolled: int = 5
    ) -> Dict[str, Any]:
        """Creates a new scheduled lecture session with lecture index budgeting (X of N)."""
        if lecture_index < 1:
            raise ValueError("Lecture index must be at least 1.")
        if total_allotted_lectures < 1:
            raise ValueError("Total allotted lectures must be at least 1.")
        if lecture_index > total_allotted_lectures:
            raise ValueError(f"Lecture index ({lecture_index}) cannot exceed total allotted lectures ({total_allotted_lectures}).")

        try:
            parsed_date = datetime.strptime(scheduled_date_str, "%Y-%m-%d").date()
        except Exception:
            parsed_date = date.today()

        date_stamp = parsed_date.strftime("%Y%m%d")
        clean_code = course_code.replace(" ", "").replace("-", "")
        lecture_id = f"LEC-{clean_code}-{date_stamp}-{lecture_index:02d}-{uuid.uuid4().hex[:4].upper()}"

        record = {
            "id": lecture_id,
            "faculty_name": faculty_name,
            "course_name": course_name,
            "course_code": course_code,
            "room_code": room_code,
            "scheduled_date": parsed_date,
            "start_time": start_time,
            "end_time": end_time,
            "lecture_index": lecture_index,
            "total_allotted_lectures": total_allotted_lectures,
            "topic": topic or f"Lecture #{lecture_index} Syllabus Delivery",
            "session_status": STATUS_SCHEDULED,
            "present_count": 0,
            "total_enrolled": total_enrolled,
            "geofence_radius_m": geofence_radius_m,
            "created_at": datetime.now(),
            "started_at": None,
            "paused_at": None,
            "resumed_at": None,
            "ended_at": None
        }

        self._live_sessions[lecture_id] = record

        try:
            with get_db_session() as db:
                db_lec = LectureSession(
                    id=lecture_id,
                    faculty_name=faculty_name,
                    course_name=course_name,
                    course_code=course_code,
                    room_code=room_code,
                    scheduled_date=parsed_date,
                    start_time=start_time,
                    end_time=end_time,
                    lecture_index=lecture_index,
                    total_allotted_lectures=total_allotted_lectures,
                    topic=record["topic"],
                    session_status=STATUS_SCHEDULED,
                    present_count=0,
                    total_enrolled=total_enrolled,
                    geofence_radius_m=geofence_radius_m,
                    created_at=record["created_at"]
                )
                db.add(db_lec)
                db.commit()
        except Exception:
            pass

        return self._format_lecture_dict(record)

    def list_faculty_lectures(self, faculty_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists lectures, optionally filtered by faculty instructor."""
        lectures = list(self._live_sessions.values())
        if faculty_name:
            norm_name = faculty_name.lower()
            lectures = [l for l in lectures if norm_name in l["faculty_name"].lower()]
        
        status_order = {STATUS_ACTIVE: 0, STATUS_PAUSED: 1, STATUS_SCHEDULED: 2, STATUS_COMPLETED: 3}
        lectures.sort(key=lambda x: (status_order.get(x["session_status"], 9), str(x["scheduled_date"]), x["lecture_index"]))
        return [self._format_lecture_dict(l) for l in lectures]

    def get_lecture(self, lecture_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single lecture by ID."""
        rec = self._live_sessions.get(lecture_id)
        return self._format_lecture_dict(rec) if rec else None

    # ----------------------------------------------------
    # 2. ATTENDANCE LIFECYCLE CONTROLLERS (START / PAUSE / RESUME / STOP)
    # ----------------------------------------------------

    def start_attendance(self, lecture_id: str, triggering_user: Optional[str] = None) -> Dict[str, Any]:
        """
        Transitions lecture status to ACTIVE.
        Enables rotating QR / 6-digit TOTP broadcast and opens student check-in verification.
        """
        lecture = self._get_or_404(lecture_id)
        
        if lecture["session_status"] == STATUS_COMPLETED:
            raise ValueError(f"Lecture {lecture_id} is already COMPLETED and locked.")

        lecture["session_status"] = STATUS_ACTIVE
        if not lecture["started_at"]:
            lecture["started_at"] = datetime.now()
        lecture["resumed_at"] = datetime.now()

        self._update_db_status(lecture_id, STATUS_ACTIVE, started_at=lecture["started_at"], resumed_at=lecture["resumed_at"])
        return self._format_lecture_dict(lecture)

    def pause_attendance(self, lecture_id: str, triggering_user: Optional[str] = None) -> Dict[str, Any]:
        """
        Transitions lecture status to PAUSED.
        Freezes the live QR/PIN display and blocks all student check-in submissions.
        """
        lecture = self._get_or_404(lecture_id)

        if lecture["session_status"] != STATUS_ACTIVE:
            raise ValueError(f"Cannot pause lecture {lecture_id} from current status '{lecture['session_status']}'. Must be ACTIVE.")

        lecture["session_status"] = STATUS_PAUSED
        lecture["paused_at"] = datetime.now()

        self._update_db_status(lecture_id, STATUS_PAUSED, paused_at=lecture["paused_at"])
        return self._format_lecture_dict(lecture)

    def resume_attendance(self, lecture_id: str, triggering_user: Optional[str] = None) -> Dict[str, Any]:
        """
        Transitions lecture status from PAUSED back to ACTIVE.
        Restores dynamic QR/PIN generation and re-opens student verification.
        """
        lecture = self._get_or_404(lecture_id)

        if lecture["session_status"] != STATUS_PAUSED:
            raise ValueError(f"Cannot resume lecture {lecture_id} from status '{lecture['session_status']}'. Must be PAUSED.")

        lecture["session_status"] = STATUS_ACTIVE
        lecture["resumed_at"] = datetime.now()

        self._update_db_status(lecture_id, STATUS_ACTIVE, resumed_at=lecture["resumed_at"])
        return self._format_lecture_dict(lecture)

    def stop_attendance(self, lecture_id: str, triggering_user: Optional[str] = None) -> Dict[str, Any]:
        """
        Transitions lecture status to COMPLETED.
        Terminates the attendance session, freezes final present counts, and commits the roster.
        """
        lecture = self._get_or_404(lecture_id)

        if lecture["session_status"] == STATUS_COMPLETED:
            return self._format_lecture_dict(lecture)

        lecture["session_status"] = STATUS_COMPLETED
        lecture["ended_at"] = datetime.now()

        self._update_db_status(lecture_id, STATUS_COMPLETED, ended_at=lecture["ended_at"])
        return self._format_lecture_dict(lecture)

    def update_present_count(self, lecture_id: str, increment: int = 1) -> int:
        """Increments present count during active check-in."""
        if lecture_id in self._live_sessions:
            self._live_sessions[lecture_id]["present_count"] = self._live_sessions[lecture_id].get("present_count", 0) + increment
            return self._live_sessions[lecture_id]["present_count"]
        return 0

    def get_lifecycle_status(self, lecture_id: str) -> str:
        """Returns current state machine status (SCHEDULED, ACTIVE, PAUSED, COMPLETED)."""
        lec = self._live_sessions.get(lecture_id)
        if lec:
            return lec.get("session_status", STATUS_SCHEDULED)
        return STATUS_ACTIVE

    # ----------------------------------------------------
    # INTERNAL HELPERS
    # ----------------------------------------------------

    def _get_or_404(self, lecture_id: str) -> Dict[str, Any]:
        if lecture_id not in self._live_sessions:
            raise KeyError(f"Lecture session '{lecture_id}' not found.")
        return self._live_sessions[lecture_id]

    def _update_db_status(self, lecture_id: str, new_status: str, **timestamps):
        try:
            with get_db_session() as db:
                db_lec = db.query(LectureSession).filter_by(id=lecture_id).first()
                if db_lec:
                    db_lec.session_status = new_status
                    for k, v in timestamps.items():
                        if hasattr(db_lec, k) and v is not None:
                            setattr(db_lec, k, v)
                    db.commit()
        except Exception:
            pass

    def _format_lecture_dict(self, lec: Dict[str, Any]) -> Dict[str, Any]:
        res = lec.copy()
        if isinstance(res.get("scheduled_date"), (date, datetime)):
            res["scheduled_date"] = res["scheduled_date"].strftime("%Y-%m-%d")
        if isinstance(res.get("created_at"), datetime):
            res["created_at"] = res["created_at"].isoformat()
        if isinstance(res.get("started_at"), datetime):
            res["started_at"] = res["started_at"].isoformat()
        if isinstance(res.get("paused_at"), datetime):
            res["paused_at"] = res["paused_at"].isoformat()
        if isinstance(res.get("resumed_at"), datetime):
            res["resumed_at"] = res["resumed_at"].isoformat()
        if isinstance(res.get("ended_at"), datetime):
            res["ended_at"] = res["ended_at"].isoformat()
        
        idx = res.get("lecture_index", 1)
        total = res.get("total_allotted_lectures", 30)
        res["syllabus_progress_pct"] = round((idx / total) * 100, 1) if total > 0 else 0.0
        return res


# Global singleton instance
lecture_manager = LectureManager()
