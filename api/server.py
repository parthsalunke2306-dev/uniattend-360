"""
FastAPI High-Performance Production REST API Server for UniAttend Analytics.
Provides RESTful endpoints for IoT hardware scanners, mobile web apps,
predictive ML inference, anti-proxy verification, and automated reporting.
Interactive OpenAPI / Swagger Documentation available at /docs.
"""

import os
import sys
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.models import (
    University, College, Department, Course, Faculty, Student, 
    TimetableSession, RawAttendanceLog, FactAttendance, StudentCourseSummary, UserAccount
)
from database.db_manager import get_db_session, init_db
from pipeline.anti_proxy_engine import anti_proxy_engine, DEFAULT_CLASSROOM_GEO
from pipeline.auth_manager import ProfileManager, ROLE_DEFINITIONS
from pipeline.lecture_manager import lecture_manager, STATUS_ACTIVE, STATUS_PAUSED, STATUS_SCHEDULED, STATUS_COMPLETED
from pipeline.etl_pipeline import AttendanceETLPipeline
from ml_engine.risk_predictor import AttendanceRiskModel
from ml_engine.proxy_detector import ProxyAnomalyDetector
from ml_engine.feature_builder import AttendanceFeatureBuilder
from reporting.excel_reporter import ExcelAttendanceReporter
from reporting.pdf_reporter import PDFReportGenerator
from reporting.automated_job import AutomatedReportingScheduler
from api.schemas import (
    HealthResponse, ActiveTokenResponse, StudentCheckInRequest,
    StudentCheckInResponse, SimulationRequest, SimulationResponse, RiskPredictionRequest,
    CreateLectureRequest, LectureResponse, LifecycleActionRequest,
    UpdateFacultyAnchorRequest, ProxyAttemptResponse,
    ResetStudentDeviceRequest, BindStudentDeviceRequest, StudentDeviceStatusResponse
)
from api.auth import auth_router, passkey_router
from api.admin import admin_router

app = FastAPI(
    title="UniAttend 360 Enterprise REST API",
    description="High-Throughput Academic Attendance, Tri-Factor Anti-Proxy Verification & Machine Learning Intelligence API.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register Authentication, RBAC, Passkey & Principal Super-Admin Routers
app.include_router(auth_router)
app.include_router(passkey_router)
app.include_router(admin_router)

# Enable CORS for frontend integration (Vercel, Localhost, Mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 1. SYSTEM & HEALTH ENDPOINTS
# ==========================================

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """System health check and uptime ping."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


# ==========================================
# 2. RBAC & PROFILE ENDPOINTS
# ==========================================

@app.get("/api/v1/roles", tags=["RBAC & Auth"])
def get_roles():
    """Returns available institutional roles (Principal, HOD, Teacher, Student) and permissions."""
    return ROLE_DEFINITIONS


@app.get("/api/v1/users", tags=["RBAC & Auth"])
def get_user_accounts(role: Optional[str] = None):
    """Returns registered user accounts, optionally filtered by role."""
    with get_db_session() as session:
        query = session.query(UserAccount)
        if role:
            query = query.filter_by(role=role.upper())
        users = query.all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "avatar_icon": u.avatar_icon,
                "university_id": u.university_id,
                "department_id": u.department_id,
                "faculty_id": u.faculty_id,
                "student_id": u.student_id
            }
            for u in users
        ]


# ==========================================
# 3. ACADEMIC HIERARCHY
# ==========================================

@app.get("/api/v1/hierarchy", tags=["Academics"])
def get_academic_hierarchy():
    """Returns full institutional hierarchy: Universities -> Colleges -> Departments -> Courses."""
    with get_db_session() as session:
        unis = session.query(University).all()
        result = []
        for u in unis:
            u_data = {"id": u.id, "name": u.name, "code": u.code, "colleges": []}
            for col in u.colleges:
                col_data = {"id": col.id, "name": col.name, "campus_code": col.campus_code, "departments": []}
                for dept in col.departments:
                    dept_data = {
                        "id": dept.id,
                        "name": dept.name,
                        "dept_code": dept.dept_code,
                        "courses": [{"id": c.id, "name": c.course_name, "code": c.course_code, "credits": c.credits} for c in dept.courses],
                        "students_count": len(dept.students),
                        "faculty_count": len(dept.faculty)
                    }
                    col_data["departments"].append(dept_data)
                u_data["colleges"].append(col_data)
            result.append(u_data)
        return result


# ==========================================
# 4. LECTURE SCHEDULING & LIFECYCLE STATE MACHINE
# ==========================================

@app.post("/api/v1/lectures/create", response_model=LectureResponse, tags=["Lecture Lifecycle"])
def create_lecture_session(req: CreateLectureRequest):
    """
    Creates a new lecture session with syllabus index budgeting (Lecture X of N allotted).
    Initial state: SCHEDULED.
    """
    try:
        lec = lecture_manager.create_lecture(
            faculty_name=req.faculty_name,
            course_name=req.course_name,
            course_code=req.course_code,
            room_code=req.room_code,
            scheduled_date_str=req.scheduled_date,
            start_time=req.start_time,
            end_time=req.end_time,
            lecture_index=req.lecture_index,
            total_allotted_lectures=req.total_allotted_lectures,
            topic=req.topic,
            geofence_radius_m=req.geofence_radius_m,
            total_enrolled=req.total_enrolled
        )
        return lec
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/lectures/faculty", response_model=List[LectureResponse], tags=["Lecture Lifecycle"])
def get_faculty_lectures(faculty_name: Optional[str] = Query(default=None)):
    """Lists all past and upcoming lecture sessions, optionally filtered by faculty member."""
    return lecture_manager.list_faculty_lectures(faculty_name=faculty_name)


@app.get("/api/v1/lectures/{lecture_id}", response_model=LectureResponse, tags=["Lecture Lifecycle"])
def get_lecture_details(lecture_id: str):
    """Retrieves lecture metadata, current state (ACTIVE/PAUSED/SCHEDULED/COMPLETED), and present count."""
    lec = lecture_manager.get_lecture(lecture_id)
    if not lec:
        raise HTTPException(status_code=404, detail=f"Lecture session '{lecture_id}' not found.")
    return lec


@app.post("/api/v1/lectures/{lecture_id}/attendance/start", response_model=LectureResponse, tags=["Lecture Lifecycle"])
def start_lecture_attendance(lecture_id: str, req: Optional[LifecycleActionRequest] = None):
    """
    Transitions lecture to ACTIVE state.
    Starts 8-second dynamic QR streaming and rolling 6-digit TOTP broadcast.
    """
    try:
        user = req.user_name if req else None
        return lecture_manager.start_attendance(lecture_id, triggering_user=user)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Lecture session '{lecture_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/lectures/{lecture_id}/attendance/pause", response_model=LectureResponse, tags=["Lecture Lifecycle"])
def pause_lecture_attendance(lecture_id: str, req: Optional[LifecycleActionRequest] = None):
    """
    Transitions lecture to PAUSED state.
    Freezes QR/PIN rotation with paused overlay and blocks student check-in submissions.
    """
    try:
        user = req.user_name if req else None
        return lecture_manager.pause_attendance(lecture_id, triggering_user=user)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Lecture session '{lecture_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/lectures/{lecture_id}/attendance/resume", response_model=LectureResponse, tags=["Lecture Lifecycle"])
def resume_lecture_attendance(lecture_id: str, req: Optional[LifecycleActionRequest] = None):
    """
    Transitions lecture from PAUSED back to ACTIVE state.
    Resumes dynamic token rotation and student verification acceptance.
    """
    try:
        user = req.user_name if req else None
        return lecture_manager.resume_attendance(lecture_id, triggering_user=user)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Lecture session '{lecture_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/lectures/{lecture_id}/attendance/stop", response_model=LectureResponse, tags=["Lecture Lifecycle"])
def stop_lecture_attendance(lecture_id: str, req: Optional[LifecycleActionRequest] = None):
    """
    Transitions lecture to COMPLETED state.
    Terminates the attendance session, locks final attendance count, and freezes roster.
    """
    try:
        user = req.user_name if req else None
        return lecture_manager.stop_attendance(lecture_id, triggering_user=user)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Lecture session '{lecture_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# 5. SMART CLASSROOM & ANTI-PROXY KIOSK
# ==========================================

@app.get("/api/v1/kiosk/token", response_model=ActiveTokenResponse, tags=["Anti-Proxy Kiosk"])
def get_active_kiosk_token(
    session_id: str = Query(default="LIVE_SESS_1_LH-101"),
    room_code: str = Query(default="LH-101")
):
    """
    Generates a micro-rotating cryptographic dynamic QR token and 6-digit security PIN.
    Refreshes every 8 seconds.
    """
    token_data = anti_proxy_engine.generate_active_token(session_id=session_id, room_code=room_code)
    qr_b64 = anti_proxy_engine.generate_qr_image_base64(token_data)

    return {
        "token": token_data["token"],
        "rolling_pin": token_data["rolling_pin"],
        "time_remaining_seconds": token_data["time_remaining_seconds"],
        "ttl_seconds": token_data["ttl_seconds"],
        "room_code": room_code,
        "qr_image_base64": qr_b64
    }


@app.post("/api/v1/attendance/geofence/update-faculty-anchor", tags=["Anti-Proxy Kiosk"])
def update_faculty_geofence_anchor(req: UpdateFacultyAnchorRequest):
    """
    Dynamically establishes the center of the geofence using the faculty device's active GPS coordinates.
    Updates the perimeter radius and accuracy lock in the active lecture session.
    """
    anchor = lecture_manager.update_faculty_anchor(
        lecture_id=req.session_id,
        lat=req.faculty_lat,
        lon=req.faculty_lon,
        accuracy_m=req.accuracy_m,
        radius_m=req.radius_m,
        anchor_source=req.anchor_source
    )
    return {
        "status": "ANCHOR_UPDATED",
        "message": f"Dynamic geofence anchor established at {req.faculty_lat:.5f}, {req.faculty_lon:.5f} (Radius: {req.radius_m}m).",
        "anchor": anchor
    }


@app.get("/api/v1/attendance/proxy-attempts", response_model=List[ProxyAttemptResponse], tags=["Anti-Proxy Kiosk"])
def list_all_proxy_attempts():
    """Returns global history of intercepted and blocked proxy attempts across all classrooms."""
    return anti_proxy_engine.get_proxy_attempts()


@app.get("/api/v1/attendance/proxy-attempts/{session_id}", response_model=List[ProxyAttemptResponse], tags=["Anti-Proxy Kiosk"])
def get_session_proxy_attempts(session_id: str):
    """Returns real-time intercepted proxy attempts and geofence breaches for a specific active lecture session."""
    return anti_proxy_engine.get_proxy_attempts(session_id=session_id)


@app.post("/api/v1/attendance/proxy-attempts/{attempt_id}/acknowledge", tags=["Anti-Proxy Kiosk"])
def acknowledge_proxy_attempt(attempt_id: str):
    """Marks a flagged proxy attempt as acknowledged/reviewed by the instructor."""
    success = anti_proxy_engine.acknowledge_proxy_attempt(attempt_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Proxy attempt incident '{attempt_id}' not found.")
    return {"status": "ACKNOWLEDGED", "incident_id": attempt_id}


@app.post("/api/v1/attendance/verify", response_model=StudentCheckInResponse, tags=["Anti-Proxy Kiosk"])
def verify_student_checkin(req: StudentCheckInRequest):
    """
    Validates a student check-in through lifecycle state validation and all 4 Anti-Proxy security shields:
      0. Lifecycle State Enforcement (must be ACTIVE; PAUSED/SCHEDULED/COMPLETED are blocked)
      1. Cryptographic Token / PIN Freshness (within 8s TTL + drift tolerance)
      2. Dynamic Haversine Geofence to Faculty Device Anchor (<= radius_m)
      3. Single-Device Hardware Binding (1 Phone = 1 Student)
      4. Duplicate Scan Prevention
    """
    # 0. Check session lifecycle status
    lifecycle_status = lecture_manager.get_lifecycle_status(req.session_id)
    if lifecycle_status == STATUS_PAUSED:
        return {
            "status": "SESSION_PAUSED",
            "is_success": False,
            "is_proxy_blocked": False,
            "distance_meters": 0.0,
            "message": "Attendance is temporarily paused by the instructor.",
            "failure_reason": "Attendance session is currently PAUSED. Submissions are temporarily blocked.",
            "attack_type": None
        }
    elif lifecycle_status == STATUS_SCHEDULED:
        return {
            "status": "SESSION_NOT_STARTED",
            "is_success": False,
            "is_proxy_blocked": False,
            "distance_meters": 0.0,
            "message": "Attendance session has not been started yet by the instructor.",
            "failure_reason": "Lecture session is SCHEDULED and not yet ACTIVE.",
            "attack_type": None
        }
    elif lifecycle_status == STATUS_COMPLETED:
        return {
            "status": "SESSION_COMPLETED",
            "is_success": False,
            "is_proxy_blocked": False,
            "distance_meters": 0.0,
            "message": "Attendance session has ended and locked.",
            "failure_reason": "Attendance session is COMPLETED. No further check-ins accepted.",
            "attack_type": None
        }

    result = anti_proxy_engine.verify_student_checkin(
        session_id=req.session_id,
        student_id_str=req.student_id_str,
        student_name=req.student_name,
        input_token_or_pin=req.input_token_or_pin,
        student_lat=req.student_lat,
        student_lon=req.student_lon,
        device_fingerprint=req.device_fingerprint,
        room_code=req.room_code
    )

    if result.get("is_success"):
        lecture_manager.update_present_count(req.session_id, 1)

    return {
        "status": result["status"],
        "is_success": result["is_success"],
        "is_proxy_blocked": result.get("is_proxy_blocked", False),
        "distance_meters": result.get("distance_meters", 0.0),
        "max_allowed_radius_m": result.get("max_allowed_radius_m", 10.0),
        "faculty_anchor": result.get("faculty_anchor"),
        "message": result.get("message"),
        "failure_reason": result.get("failure_reason"),
        "attack_type": result.get("attack_type"),
        "incident_id": result.get("incident_id")
    }


# ==========================================
# 5A. 1-DEVICE HARDWARE LOCK & EMERGENCY RESET
# ==========================================

@app.post("/api/v1/attendance/device/reset", tags=["Hardware Device Security"])
def reset_student_device_lock(req: ResetStudentDeviceRequest):
    """
    Emergency Administrative Reset:
    Allows Faculty, HOD, or Admin to reset a student's hardware device lock (e.g. phone lost or upgraded).
    """
    result = anti_proxy_engine.reset_student_device(
        student_id_str=req.student_id_str,
        authorized_by=req.authorized_by
    )
    return result


@app.get("/api/v1/attendance/device/status/{student_id_str}", response_model=StudentDeviceStatusResponse, tags=["Hardware Device Security"])
def get_student_device_status(student_id_str: str):
    """Retrieves current 1-device hardware lock binding status for a student."""
    return anti_proxy_engine.get_student_device_status(student_id_str)


@app.post("/api/v1/attendance/device/bind", tags=["Hardware Device Security"])
def bind_student_device(req: BindStudentDeviceRequest):
    """Binds a student's primary physical smartphone to their attendance profile."""
    result = anti_proxy_engine.bind_student_device(
        student_id_str=req.student_id_str,
        device_uuid=req.device_uuid,
        device_name=req.device_name or "Primary Smartphone"
    )
    return {
        "status": "DEVICE_BOUND",
        "student_id_str": req.student_id_str,
        "device_info": result,
        "message": f"Successfully locked account {req.student_id_str} to device {req.device_uuid[:12]}..."
    }


# ==========================================
# 5. ANALYTICS & EXECUTIVE SUMMARIES
# ==========================================

@app.get("/api/v1/analytics/campus-summary", tags=["Analytics"])
def get_campus_summary(university_id: int = 1):
    """Returns high-level institutional health metrics and cross-department performance."""
    with get_db_session() as session:
        uni = session.get(University, university_id)
        if not uni:
            raise HTTPException(status_code=404, detail="University not found")

        dept_ids = [d.id for col in uni.colleges for d in col.departments]
        courses = session.query(Course).filter(Course.department_id.in_(dept_ids)).all()
        c_ids = [c.id for c in courses]
        
        summaries = session.query(StudentCourseSummary).filter(
            StudentCourseSummary.course_id.in_(c_ids)
        ).all()

        total_students = session.query(Student).filter(Student.department_id.in_(dept_ids)).count()
        total_enrollments = len(summaries)
        defaulters = [s for s in summaries if s.is_defaulter]
        avg_pct = (sum(s.attendance_pct for s in summaries) / total_enrollments) if total_enrollments else 0.0

        return {
            "university_name": uni.name,
            "total_students": total_students,
            "total_departments": len(dept_ids),
            "average_attendance_pct": round(avg_pct, 2),
            "total_defaulter_cases": len(defaulters),
            "defaulter_rate_pct": round((len(defaulters)/total_enrollments*100), 2) if total_enrollments else 0.0
        }


@app.get("/api/v1/student/{student_id}/profile", tags=["Student 360"])
def get_student_profile(student_id: int):
    """Returns Student 360 profile, enrolled courses, and attendance percentages."""
    with get_db_session() as session:
        student = session.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        summaries = session.query(StudentCourseSummary).filter_by(student_id=student.id).all()
        course_map = {c.id: c for c in session.query(Course).all()}

        courses_data = []
        for s in summaries:
            c_obj = course_map.get(s.course_id)
            courses_data.append({
                "course_code": c_obj.course_code if c_obj else "N/A",
                "course_name": c_obj.course_name if c_obj else "N/A",
                "total_held": s.total_classes,
                "attended": s.attended_classes,
                "late": s.late_classes,
                "absent": s.absent_classes,
                "attendance_pct": s.attendance_pct,
                "is_defaulter": s.is_defaulter,
                "classes_needed_for_75": s.classes_needed_for_75,
                "risk_category": s.risk_category
            })

        overall_pct = (sum(s.attendance_pct for s in summaries) / len(summaries)) if summaries else 0.0

        return {
            "student_id": student.id,
            "roll_no": student.student_id_str,
            "full_name": student.full_name,
            "email": student.email,
            "semester": student.semester,
            "batch_year": student.batch_year,
            "overall_attendance_pct": round(overall_pct, 2),
            "is_eligible_for_exams": overall_pct >= 75.0,
            "courses": courses_data
        }


@app.post("/api/v1/student/simulate", response_model=SimulationResponse, tags=["Student 360"])
def simulate_attendance(req: SimulationRequest):
    """Simulates how future class attendance will impact final eligibility."""
    new_held = req.current_held + req.upcoming_to_attend + req.upcoming_to_miss
    new_att = req.current_attended + req.upcoming_to_attend
    new_pct = (new_att / new_held * 100.0) if new_held > 0 else 0.0
    is_eligible = new_pct >= req.target_pct

    needed = 0
    if not is_eligible:
        # (new_att + N) / (new_held + N) >= target_pct / 100
        target = req.target_pct / 100.0
        needed = max(0, int((target * new_held - new_att) / (1.0 - target))) + 1

    return {
        "projected_held": new_held,
        "projected_attended": new_att,
        "projected_attendance_pct": round(new_pct, 2),
        "is_eligible": is_eligible,
        "additional_classes_needed": needed
    }


# ==========================================
# 6. ML PREDICTIVE & ANOMALY RADAR
# ==========================================

@app.post("/api/v1/ml/predict-risk", tags=["Machine Learning"])
def predict_attendance_risk(req: RiskPredictionRequest):
    """ML endpoint predicting whether an at-risk student will fail the 75% threshold."""
    ml = AttendanceRiskModel()
    pred = ml.predict_risk(req.dict())
    return pred


@app.get("/api/v1/anomalies/audit", tags=["Machine Learning"])
def audit_proxy_anomalies():
    """Runs proxy anomaly radar detecting impossible travel speeds and card dumping."""
    with get_db_session() as session:
        detector = ProxyAnomalyDetector(session)
        audit_res = detector.run_full_anomaly_audit()
        return audit_res


# ==========================================
# 7. AUTOMATED REPORTING & EXPORT
# ==========================================

@app.post("/api/v1/reports/trigger-nightly-audit", tags=["Automated Reporting"])
def trigger_nightly_reporting_audit():
    """Triggers the automated batch ELT and report generation pipeline."""
    scheduler = AutomatedReportingScheduler()
    res = scheduler.run_nightly_batch_job()
    return res


@app.get("/api/v1/reports/excel/{department_id}", tags=["Automated Reporting"])
def download_department_excel(department_id: int):
    """Generates and returns the Master Department Excel workbook."""
    with get_db_session() as session:
        reporter = ExcelAttendanceReporter()
        filepath = reporter.generate_department_master_report(session, department_id)
        return FileResponse(
            filepath,
            filename=os.path.basename(filepath),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


@app.get("/api/v1/reports/pdf/{department_id}", tags=["Automated Reporting"])
def download_department_pdf(department_id: int):
    """Generates and returns the Executive Department PDF report."""
    with get_db_session() as session:
        pdf_gen = PDFReportGenerator()
        filepath = pdf_gen.generate_department_executive_pdf(session, department_id)
        return FileResponse(
            filepath,
            filename=os.path.basename(filepath),
            media_type="application/pdf"
        )


@app.get("/api/v1/reports/letter/{student_id}", tags=["Automated Reporting"])
def download_student_warning_letter(student_id: int):
    """Generates and returns the personalized Student Attendance Deficiency Notice PDF."""
    with get_db_session() as session:
        pdf_gen = PDFReportGenerator()
        filepath = pdf_gen.generate_student_warning_letter_pdf(session, student_id)
        return FileResponse(
            filepath,
            filename=os.path.basename(filepath),
            media_type="application/pdf"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
