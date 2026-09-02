"""
UniAttend Analytics - Database Models & Multi-Tenant Star Schema
SQLAlchemy 2.0 ORM definitions supporting Multi-Tenancy (University -> College -> Department)
and a Medallion Architecture (Bronze: Raw Logs -> Silver: Fact Attendance -> Gold: Summary Marts).
"""

from datetime import datetime, date, time
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Time, 
    ForeignKey, Index, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ==========================================
# 1. TENANT & INSTITUTIONAL HIERARCHY
# ==========================================

class University(Base):
    """Top-level tenant representing a University or Academic Board."""
    __tablename__ = "universities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    colleges = relationship("College", back_populates="university", cascade="all, delete-orphan")


class College(Base):
    """Institutional entity under a University (e.g. School of Engineering)."""
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False)
    name = Column(String(200), nullable=False)
    campus_code = Column(String(30), nullable=False)
    city = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    university = relationship("University", back_populates="colleges")
    departments = relationship("Department", back_populates="college", cascade="all, delete-orphan")


class Department(Base):
    """Department within a College (e.g. Computer Science, Data Science)."""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    name = Column(String(150), nullable=False)
    dept_code = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    college = relationship("College", back_populates="departments")
    courses = relationship("Course", back_populates="department", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="department", cascade="all, delete-orphan")
    faculty = relationship("Faculty", back_populates="department", cascade="all, delete-orphan")


# ==========================================
# 2. ACADEMIC & PEOPLE DIMENSIONS
# ==========================================

class Course(Base):
    """Academic course or subject module."""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    course_name = Column(String(150), nullable=False)
    course_code = Column(String(30), nullable=False, unique=True)
    credits = Column(Integer, default=3)
    semester = Column(Integer, default=1)
    minimum_attendance_pct = Column(Float, default=75.0)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    department = relationship("Department", back_populates="courses")
    sessions = relationship("TimetableSession", back_populates="course", cascade="all, delete-orphan")
    attendance_facts = relationship("FactAttendance", back_populates="course")


class Faculty(Base):
    """Instructors / Professors managing course sessions."""
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    faculty_id_str = Column(String(50), nullable=False, unique=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    designation = Column(String(100), default="Assistant Professor")

    # Relationships
    department = relationship("Department", back_populates="faculty")
    sessions = relationship("TimetableSession", back_populates="faculty")


class Student(Base):
    """Student dimension."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    student_id_str = Column(String(50), nullable=False, unique=True)  # Roll number / Enrollment ID
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    batch_year = Column(Integer, default=2024)
    semester = Column(Integer, default=1)
    rfid_card_id = Column(String(100), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    department = relationship("Department", back_populates="students")
    attendance_facts = relationship("FactAttendance", back_populates="student")


class TimetableSession(Base):
    """Scheduled lecture or lab session for a course."""
    __tablename__ = "timetable_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    room_number = Column(String(50), nullable=False)
    day_of_week = Column(String(15), nullable=False)  # Monday, Tuesday, etc.
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    session_type = Column(String(30), default="Lecture")  # Lecture, Lab, Seminar

    # Relationships
    course = relationship("Course", back_populates="sessions")
    faculty = relationship("Faculty", back_populates="sessions")
    attendance_facts = relationship("FactAttendance", back_populates="session")


class LectureSession(Base):
    """
    Specific dated lecture instance with lecture index budgeting (X of N allotted)
    and real-time attendance lifecycle state machine (SCHEDULED, ACTIVE, PAUSED, COMPLETED).
    """
    __tablename__ = "lecture_sessions"

    id = Column(String(100), primary_key=True)  # e.g., "LEC-DS201-20260823-14"
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    faculty_name = Column(String(150), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    course_code = Column(String(50), nullable=False)  # e.g. "DS201-DM"
    course_name = Column(String(150), nullable=False)  # e.g. "Data Mining (Theory)"
    room_code = Column(String(50), nullable=False, default="E-104")
    
    # Scheduling & Index metadata
    scheduled_date = Column(Date, nullable=False, default=date.today)
    start_time = Column(String(20), nullable=False, default="09:00 AM")
    end_time = Column(String(20), nullable=False, default="10:00 AM")
    lecture_index = Column(Integer, nullable=False, default=1)  # e.g. 14
    total_allotted_lectures = Column(Integer, nullable=False, default=30)  # e.g. 30
    topic = Column(String(255), nullable=True)  # e.g. "Apriori Algorithm & Association Mining"
    
    # State Machine: SCHEDULED, ACTIVE, PAUSED, COMPLETED
    session_status = Column(String(30), nullable=False, default="SCHEDULED")
    
    # Metrics & Dynamic Geofence
    present_count = Column(Integer, default=0, nullable=False)
    total_enrolled = Column(Integer, default=5, nullable=False)
    geofence_radius_m = Column(Float, default=10.0, nullable=False)
    faculty_lat = Column(Float, nullable=True, default=19.22170)
    faculty_lon = Column(Float, nullable=True, default=73.16460)
    faculty_accuracy_m = Column(Float, nullable=True, default=3.0)
    anchor_source = Column(String(50), default="DEVICE_GPS")  # DEVICE_GPS, ROOM_PRESET, MANUAL
    
    # Lifecycle Timestamps
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    resumed_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)


class ProxyAttemptLog(Base):
    """
    Real-time security incident log capturing out-of-perimeter geofence breaches,
    device hardware sharing, replay attacks, and expired QR tokens.
    """
    __tablename__ = "proxy_attempt_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    student_id_str = Column(String(50), nullable=False, index=True)
    student_name = Column(String(150), nullable=False)
    attack_type = Column(String(50), nullable=False, index=True)  # GEOFENCE_BREACH_OUT_OF_RANGE, DEVICE_SHARING_PROXY, EXPIRED_QR_PROXY
    student_lat = Column(Float, nullable=True)
    student_lon = Column(Float, nullable=True)
    faculty_anchor_lat = Column(Float, nullable=True)
    faculty_anchor_lon = Column(Float, nullable=True)
    distance_meters = Column(Float, nullable=True)
    max_allowed_radius_m = Column(Float, nullable=True)
    device_fingerprint = Column(String(150), nullable=True)
    failure_reason = Column(String(255), nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, index=True)


# ==========================================
# 3. BRONZE LAYER (RAW DEVICE SWIPE LOGS)
# ==========================================

class RawAttendanceLog(Base):
    """Raw ingestion buffer capturing biometric, RFID, and QR scan events."""
    __tablename__ = "bronze_raw_attendance_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_device_id = Column(String(100), nullable=False)
    student_id_str = Column(String(50), nullable=False, index=True)
    scan_timestamp = Column(DateTime, nullable=False, index=True)
    scan_method = Column(String(50), default="RFID")  # RFID, QR_CODE, BIOMETRIC, FACIAL_RECOGNITION
    room_code = Column(String(50), nullable=False)
    device_ip_or_geo = Column(String(100), nullable=True)
    ingested_at = Column(DateTime, default=datetime.now)
    
    # ELT processing status
    processing_status = Column(String(30), default="PENDING")  # PENDING, PROCESSED, REJECTED_DUPLICATE, REJECTED_OUT_OF_WINDOW
    rejection_reason = Column(String(255), nullable=True)


# ==========================================
# 4. SILVER LAYER (FACT ATTENDANCE)
# ==========================================

class FactAttendance(Base):
    """Validated, normalized, session-linked student attendance records."""
    __tablename__ = "silver_fact_attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timetable_session_id = Column(Integer, ForeignKey("timetable_sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    session_date = Column(Date, nullable=False, index=True)
    checkin_time = Column(DateTime, nullable=True)
    
    # Status: PRESENT, LATE, ABSENT, EXCUSED
    status = Column(String(20), nullable=False, default="ABSENT")
    is_late = Column(Boolean, default=False)
    is_proxy_suspected = Column(Boolean, default=False)
    confidence_score = Column(Float, default=1.0)
    validation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Unique constraint per student, session, and date
    __table_args__ = (
        UniqueConstraint("student_id", "timetable_session_id", "session_date", name="uq_student_session_date"),
        Index("idx_fact_student_course_date", "student_id", "course_id", "session_date"),
    )

    # Relationships
    student = relationship("Student", back_populates="attendance_facts")
    course = relationship("Course", back_populates="attendance_facts")
    session = relationship("TimetableSession", back_populates="attendance_facts")


# ==========================================
# 5. GOLD LAYER (ANALYTICS & SUMMARY MARTS)
# ==========================================

class StudentCourseSummary(Base):
    """Gold aggregate table for high-performance reporting & ML features."""
    __tablename__ = "gold_student_course_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    total_classes = Column(Integer, default=0)
    attended_classes = Column(Integer, default=0)
    late_classes = Column(Integer, default=0)
    absent_classes = Column(Integer, default=0)
    attendance_pct = Column(Float, default=0.0)
    
    # Defaulter tracking (<75% threshold)
    is_defaulter = Column(Boolean, default=False)
    classes_needed_for_75 = Column(Integer, default=0)
    can_afford_to_miss = Column(Integer, default=0)
    
    # ML Forecasts & Risk
    predicted_final_pct = Column(Float, nullable=True)
    risk_score = Column(Float, default=0.0)  # 0.0 (Safe) - 100.0 (Critical)
    risk_category = Column(String(30), default="SAFE")  # SAFE, WARNING, CRITICAL
    
    last_updated = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_summary_student_course"),
    )


# ==========================================
# 6. ROLE-BASED ACCESS & USER ACCOUNTS (RBAC)
# ==========================================

class UserAccount(Base):
    """User account model for Principal, HOD, Teacher, and Student profiles."""
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False, default="")  # Argon2id / bcrypt hash
    full_name = Column(String(150), nullable=False)
    # Roles: PRINCIPAL, COORDINATOR, TEACHER, STUDENT, ADMIN
    role = Column(String(30), nullable=False, default="STUDENT")
    
    # Associated Entity Foreign Keys
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    
    avatar_icon = Column(String(50), default="👤")
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Brute-force & Lockout Protection
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    lockout_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_failed_login_at = Column(DateTime, nullable=True)
    
    # 2-Step Verification (MFA)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_type = Column(String(30), default="TOTP")  # TOTP, WEBAUTHN, EMAIL_FALLBACK
    
    # First-Login Security & Hardware Enclave Binding
    must_change_password = Column(Boolean, default=False, nullable=False)
    is_device_bound = Column(Boolean, default=False, nullable=False)
    bound_device_name = Column(String(150), nullable=True)
    bound_device_uuid = Column(String(150), nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    mfa_config = relationship("UserMFA", back_populates="user", uselist=False, cascade="all, delete-orphan")
    passkeys = relationship("UserPasskey", back_populates="user", cascade="all, delete-orphan")
    recovery_codes = relationship("UserRecoveryCode", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("SecurityAuditLog", back_populates="user", cascade="all, delete-orphan")


class UserMFA(Base):
    """TOTP 2-Step Verification configuration for User Accounts."""
    __tablename__ = "user_mfa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, unique=True)
    secret_key = Column(String(128), nullable=False)  # Base32 TOTP secret
    is_verified = Column(Boolean, default=False, nullable=False)
    last_used_timestep = Column(Integer, default=0, nullable=False)  # Replay attack prevention
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("UserAccount", back_populates="mfa_config")


class UserRecoveryCode(Base):
    """Single-use emergency recovery codes for MFA bypass recovery."""
    __tablename__ = "user_recovery_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)  # Argon2id/bcrypt hashed
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("UserAccount", back_populates="recovery_codes")


class UserPasskey(Base):
    """W3C WebAuthn / FIDO2 / Passkey biometric credential (zero raw biometrics stored)."""
    __tablename__ = "user_passkeys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id = Column(String(255), nullable=False, unique=True, index=True)
    public_key = Column(Text, nullable=False)  # Base64 encoded public key
    sign_count = Column(Integer, default=0, nullable=False)  # Clone/replay detector
    device_name = Column(String(150), nullable=False, default="Biometric Passkey")
    transports = Column(String(100), default="internal")  # internal (FaceID/TouchID/WindowsHello), hybrid, usb
    aaguid = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("UserAccount", back_populates="passkeys")


class UserSession(Base):
    """Active user sessions and trusted devices with cryptographic revocation tracking."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(255), nullable=False, unique=True, index=True)
    device_fingerprint = Column(String(150), nullable=False)
    device_name = Column(String(150), nullable=False, default="Web Browser")
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    is_trusted = Column(Boolean, default=False, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    last_activity_at = Column(DateTime, default=datetime.now)

    user = relationship("UserAccount", back_populates="sessions")


class SecurityAuditLog(Base):
    """Append-only security audit log recording authentication and authorization events."""
    __tablename__ = "security_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="INFO", nullable=False)  # INFO, WARNING, CRITICAL
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    device_fingerprint = Column(String(150), nullable=True)
    details = Column(Text, nullable=True)  # JSON metadata (NEVER secrets or passwords)
    created_at = Column(DateTime, default=datetime.now, index=True)

    user = relationship("UserAccount", back_populates="audit_logs")


class LoginAttempt(Base):
    """Tracks failed and successful login attempts for rate-limiting and brute-force detection."""
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), nullable=False, index=True)
    ip_address = Column(String(64), nullable=True, index=True)
    success = Column(Boolean, default=False, nullable=False)
    attempted_at = Column(DateTime, default=datetime.now, index=True)

