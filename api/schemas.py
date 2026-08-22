"""
Pydantic Schemas for UniAttend Analytics REST API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "2.0.0"
    timestamp: str


class ActiveTokenResponse(BaseModel):
    token: str
    rolling_pin: str
    time_remaining_seconds: float
    ttl_seconds: int
    room_code: str
    qr_image_base64: str


class StudentCheckInRequest(BaseModel):
    session_id: str = Field(..., example="LIVE_SESS_1_LH-101")
    student_id_str: str = Field(..., example="ANU-ENG-CSE-2024-001")
    student_name: str = Field(..., example="Alex Chen")
    input_token_or_pin: str = Field(..., example="8492")
    student_lat: float = Field(..., example=28.54508)
    student_lon: float = Field(..., example=77.19270)
    device_fingerprint: str = Field(..., example="DEVICE-UUID-001")
    room_code: str = Field(default="LH-101", example="LH-101")


class StudentCheckInResponse(BaseModel):
    status: str
    is_success: bool
    is_proxy_blocked: bool
    distance_meters: float
    message: Optional[str] = None
    failure_reason: Optional[str] = None
    attack_type: Optional[str] = None


class SimulationRequest(BaseModel):
    current_held: int = Field(..., example=24)
    current_attended: int = Field(..., example=16)
    upcoming_to_attend: int = Field(default=5, example=5)
    upcoming_to_miss: int = Field(default=0, example=0)
    target_pct: float = Field(default=75.0, example=75.0)


class SimulationResponse(BaseModel):
    projected_held: int
    projected_attended: int
    projected_attendance_pct: float
    is_eligible: bool
    additional_classes_needed: int


class RiskPredictionRequest(BaseModel):
    current_attendance_pct: float = Field(..., example=62.0)
    early_attendance_pct: float = Field(default=78.0, example=78.0)
    momentum_slope: float = Field(default=-16.0, example=-16.0)
    friday_absence_rate: float = Field(default=0.55, example=0.55)
    morning_absence_rate: float = Field(default=0.40, example=0.40)
    late_ratio: float = Field(default=0.30, example=0.30)
    max_absent_streak: int = Field(default=4, example=4)
    course_credits: int = Field(default=4, example=4)


# ==========================================
# LECTURE & LIFECYCLE SCHEMAS
# ==========================================

class CreateLectureRequest(BaseModel):
    faculty_name: str = Field(default="Miss Razia Khan", example="Miss Razia Khan")
    course_name: str = Field(..., example="Data Mining (Theory)")
    course_code: str = Field(default="DS201-DM", example="DS201-DM")
    room_code: str = Field(default="E-104", example="E-104")
    scheduled_date: str = Field(..., example="2026-08-23")
    start_time: str = Field(default="09:00 AM", example="09:00 AM")
    end_time: str = Field(default="10:00 AM", example="10:00 AM")
    lecture_index: int = Field(..., ge=1, example=14)
    total_allotted_lectures: int = Field(default=30, ge=1, example=30)
    topic: Optional[str] = Field(None, example="Frequent Itemset Mining & Apriori Algorithm")
    geofence_radius_m: float = Field(default=10.0, example=10.0)
    total_enrolled: int = Field(default=5, example=5)


class LectureResponse(BaseModel):
    id: str
    faculty_name: str
    course_name: str
    course_code: str
    room_code: str
    scheduled_date: str
    start_time: str
    end_time: str
    lecture_index: int
    total_allotted_lectures: int
    topic: Optional[str] = None
    session_status: str
    present_count: int
    total_enrolled: int
    geofence_radius_m: float
    syllabus_progress_pct: float
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    resumed_at: Optional[str] = None
    ended_at: Optional[str] = None


class LifecycleActionRequest(BaseModel):
    user_name: Optional[str] = Field(default=None, example="Miss Razia Khan")
    role: Optional[str] = Field(default="TEACHER", example="TEACHER")

