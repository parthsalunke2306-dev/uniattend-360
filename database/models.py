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
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    full_name = Column(String(150), nullable=False)
    # Roles: PRINCIPAL, HOD, TEACHER, STUDENT
    role = Column(String(30), nullable=False, default="STUDENT")
    
    # Associated Entity Foreign Keys
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    
    avatar_icon = Column(String(50), default="👤")
    created_at = Column(DateTime, default=datetime.now)

