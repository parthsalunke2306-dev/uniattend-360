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
    session_id: str = Field(..., examples=["LIVE_SESS_1_LH-101"])
    student_id_str: str = Field(..., examples=["ANU-ENG-CSE-2024-001"])
    student_name: str = Field(..., examples=["Alex Chen"])
    input_token_or_pin: str = Field(..., examples=["8492"])
    student_lat: float = Field(..., examples=[28.54508])
    student_lon: float = Field(..., examples=[77.19270])
    device_fingerprint: str = Field(..., examples=["DEVICE-UUID-001"])
    room_code: str = Field(default="LH-101", examples=["LH-101"])


class StudentCheckInResponse(BaseModel):
    status: str
    is_success: bool
    is_proxy_blocked: bool
    distance_meters: float
    max_allowed_radius_m: Optional[float] = 10.0
    faculty_anchor: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    failure_reason: Optional[str] = None
    attack_type: Optional[str] = None
    incident_id: Optional[str] = None


class UpdateFacultyAnchorRequest(BaseModel):
    session_id: str = Field(..., examples=["LEC-DS201-20260823-14"])
    faculty_lat: float = Field(..., examples=[19.22170])
    faculty_lon: float = Field(..., examples=[73.16460])
    accuracy_m: float = Field(default=3.0, examples=[3.0])
    radius_m: float = Field(default=10.0, examples=[10.0])
    anchor_source: str = Field(default="DEVICE_GPS", examples=["DEVICE_GPS"])


class ProxyAttemptResponse(BaseModel):
    id: str
    session_id: str
    student_id_str: str
    student_name: str
    attack_type: str
    student_lat: Optional[float] = None
    student_lon: Optional[float] = None
    faculty_anchor_lat: Optional[float] = None
    faculty_anchor_lon: Optional[float] = None
    distance_meters: Optional[float] = None
    max_allowed_radius_m: Optional[float] = 10.0
    device_fingerprint: Optional[str] = None
    failure_reason: str
    is_acknowledged: bool = False
    timestamp: str
    created_at: Optional[str] = None


class SimulationRequest(BaseModel):
    current_held: int = Field(..., examples=[24])
    current_attended: int = Field(..., examples=[16])
    upcoming_to_attend: int = Field(default=5, examples=[5])
    upcoming_to_miss: int = Field(default=0, examples=[0])
    target_pct: float = Field(default=75.0, examples=[75.0])


class SimulationResponse(BaseModel):
    projected_held: int
    projected_attended: int
    projected_attendance_pct: float
    is_eligible: bool
    additional_classes_needed: int


class RiskPredictionRequest(BaseModel):
    current_attendance_pct: float = Field(..., examples=[62.0])
    early_attendance_pct: float = Field(default=78.0, examples=[78.0])
    momentum_slope: float = Field(default=-16.0, examples=[-16.0])
    friday_absence_rate: float = Field(default=0.55, examples=[0.55])
    morning_absence_rate: float = Field(default=0.40, examples=[0.40])
    late_ratio: float = Field(default=0.30, examples=[0.30])
    max_absent_streak: int = Field(default=4, examples=[4])
    course_credits: int = Field(default=4, examples=[4])


# ==========================================
# LECTURE & LIFECYCLE SCHEMAS
# ==========================================

class CreateLectureRequest(BaseModel):
    faculty_name: str = Field(default="Miss Razia Khan", examples=["Miss Razia Khan"])
    course_name: str = Field(..., examples=["Data Mining (Theory)"])
    course_code: str = Field(default="DS201-DM", examples=["DS201-DM"])
    room_code: str = Field(default="E-104", examples=["E-104"])
    scheduled_date: str = Field(..., examples=["2026-08-23"])
    start_time: str = Field(default="09:00 AM", examples=["09:00 AM"])
    end_time: str = Field(default="10:00 AM", examples=["10:00 AM"])
    lecture_index: int = Field(..., ge=1, examples=[14])
    total_allotted_lectures: int = Field(default=30, ge=1, examples=[30])
    topic: Optional[str] = Field(None, examples=["Frequent Itemset Mining & Apriori Algorithm"])
    geofence_radius_m: float = Field(default=10.0, examples=[10.0])
    total_enrolled: int = Field(default=5, examples=[5])


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
    faculty_lat: Optional[float] = 19.22170
    faculty_lon: Optional[float] = 73.16460
    faculty_accuracy_m: Optional[float] = 3.0
    anchor_source: Optional[str] = "DEVICE_GPS"
    syllabus_progress_pct: float
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    resumed_at: Optional[str] = None
    ended_at: Optional[str] = None


class LifecycleActionRequest(BaseModel):
    user_name: Optional[str] = Field(default=None, examples=["Miss Razia Khan"])
    role: Optional[str] = Field(default="TEACHER", examples=["TEACHER"])


# ==========================================
# HARDWARE WEBAUTHN & 1-DEVICE LOCK SCHEMAS
# ==========================================

class ResetStudentDeviceRequest(BaseModel):
    student_id_str: str = Field(..., examples=["CHMC-DS-2024-001"])
    authorized_by: str = Field(default="Miss Razia Khan", examples=["Miss Razia Khan"])
    reason: Optional[str] = Field(default="Phone upgraded / Hardware lost", examples=["Phone upgraded"])


class BindStudentDeviceRequest(BaseModel):
    student_id_str: str = Field(..., examples=["CHMC-DS-2024-001"])
    device_uuid: str = Field(..., examples=["DEV-IPHONE15PRO-SECURE-ENCLAVE"])
    device_name: Optional[str] = Field(default="Apple iPhone 15 Pro", examples=["Apple iPhone 15 Pro"])


class StudentDeviceStatusResponse(BaseModel):
    student_id_str: str
    is_locked: bool
    device_info: Optional[Dict[str, Any]] = None


# ==========================================
# PRINCIPAL SUPER-ADMIN AUTHORITY SCHEMAS
# ==========================================

class AdminDirectEnrollStudentRequest(BaseModel):
    full_name: str = Field(..., examples=["Aarav Sharma"])
    email: str = Field(..., examples=["aarav.sharma@chmc.edu"])
    identifier: str = Field(..., description="Student Roll Number (e.g. CHMC-DS-2024-006)", examples=["CHMC-DS-2024-006"])
    department_code: str = Field(default="DS", description="Department Code: DS, CS, IT, AIDS", examples=["DS"])
    batch_year: Optional[int] = Field(default=2024, examples=[2024])
    semester: Optional[int] = Field(default=3, examples=[3])
    initial_password: Optional[str] = Field(default="CHMC@2026!", examples=["CHMC@2026!"])
    expedited: Optional[bool] = Field(default=True)
    authorized_by: Optional[str] = Field(default="Dr. Manju Lalwani Pathak (Principal)", examples=["Dr. Manju Lalwani Pathak (Principal)"])


class AdminExpelStudentRequest(BaseModel):
    reason: str = Field(..., description="Institutional reason for expulsion or deletion", examples=["Disciplinary expulsion per College Academic Disciplinary Committee"])
    expulsion_type: Optional[str] = Field(default="DISCIPLINARY", examples=["DISCIPLINARY"]) # DISCIPLINARY, ADMISSION_CANCELLED, TRANSFER_OFFBOARDING, TEST_PURGE
    authorized_by: Optional[str] = Field(default="Dr. Manju Lalwani Pathak (Principal)", examples=["Dr. Manju Lalwani Pathak (Principal)"])
    confirm_roll_no: str = Field(..., description="Roll number verification check", examples=["CHMC-DS-2024-006"])


class AdminStudentResponse(BaseModel):
    id: int
    student_id_str: str
    full_name: str
    email: str
    department_code: str
    department_name: str
    batch_year: int
    semester: int
    total_classes: int
    attended_classes: int
    attendance_pct: float
    is_defaulter: bool
    is_device_locked: bool
    device_name: Optional[str] = None
    account_active: bool = True
    created_at: Optional[str] = None


class AdminAuditLogEntry(BaseModel):
    id: int
    event_type: str
    severity: str
    actor_name: str
    target_identifier: Optional[str] = None
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None
    details: Dict[str, Any] = {}
    created_at: str


class AdminProvisionUserRequest(BaseModel):
    category: str = Field(default="STUDENT", description="Account Category: STUDENT, FACULTY, COORDINATOR, ADMIN_STAFF")
    full_name: str = Field(...)
    email: str = Field(...)
    identifier: str = Field(..., description="Roll Number, Faculty ID, or Staff ID")
    department_code: Optional[str] = Field(default="DS", description="Department Code: DS, CS, IT, AIDS, ADMIN")
    designation: Optional[str] = Field(default=None)
    batch_year: Optional[int] = Field(default=2024)
    semester: Optional[int] = Field(default=3)
    division: Optional[str] = Field(default="A")
    initial_password: Optional[str] = Field(default="CHMC@2026!")
    expedited: Optional[bool] = Field(default=True)
    authorized_by: Optional[str] = Field(default="Mr. Sanjay Mehta (Admin Office)")



