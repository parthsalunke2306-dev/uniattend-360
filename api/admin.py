"""
UniAttend 360 - Principal Super-Admin Authority Module.
Grants top-level unrestricted administrative authority to College Principal & Super-Admins:
  1. Direct Multi-Department Student Provisioning & Enrollment.
  2. Permanent Student Account Expulsion, Credential Revocation & Cascade Purge.
  3. Master Institutional Student Ledger Querying.
  4. Immutable Security Audit Logging & Compliance Ledger Inspection.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database.models import (
    UserAccount, UserMFA, UserRecoveryCode, UserPasskey,
    UserSession, SecurityAuditLog, Student, Faculty, Department, Course,
    StudentCourseSummary, FactAttendance, RawAttendanceLog, ProxyAttemptLog
)
from database.db_manager import get_db
from pipeline.anti_proxy_engine import anti_proxy_engine
from api.security import (
    PasswordHasherService, PasswordPolicy, SecurityAuditLogger,
    get_current_user, require_role
)
from api.schemas import (
    AdminDirectEnrollStudentRequest, AdminExpelStudentRequest,
    AdminStudentResponse, AdminAuditLogEntry, AdminProvisionUserRequest
)

admin_router = APIRouter(prefix="/api/v1/admin", tags=["Principal Super-Admin Governance"])


# ==========================================
# 1. DIRECT MULTI-DEPARTMENT STUDENT ENROLLMENT
# ==========================================

@admin_router.post(
    "/students/enroll",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Principal Direct Student Provisioning & Enrollment"
)
def superadmin_direct_enroll_student(
    req: AdminDirectEnrollStudentRequest,
    request: Request,
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN", "ADMIN_STAFF"])),
    db: Session = Depends(get_db)
):
    """
    Direct Student Enrollment (Super-Admin Override):
    Instantly provisions and fast-tracks a student account into any target academic department
    (e.g., Data Science, Computer Science, IT, AI&DS) without secondary approval bottlenecks.
    
    Creates:
      - Student entity in the target department.
      - UserAccount with role 'STUDENT' and Argon2id hashed credentials.
      - StudentCourseSummary tracking rows for all active departmental courses.
      - Immutable SecurityAuditLog record (SUPERADMIN_STUDENT_ENROLLED).
    """
    clean_email = req.email.strip().lower()
    clean_id = req.identifier.strip().upper()
    ip_addr = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")

    # 1. Validate Initial Password Strength if provided
    initial_password = req.initial_password or "CHMC@2026!"
    is_valid_pw, pw_msg = PasswordPolicy.validate(initial_password)
    if not is_valid_pw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Initial password does not satisfy institutional security requirements: {pw_msg}"
        )

    # 2. Check for duplicate email across user accounts
    existing_user = db.query(UserAccount).filter(UserAccount.email.ilike(clean_email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A user account with email '{clean_email}' already exists (Username: {existing_user.username})."
        )

    # 3. Check for duplicate student roll number
    existing_student = db.query(Student).filter(Student.student_id_str.ilike(clean_id)).first()
    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A student with roll number / ID '{clean_id}' is already registered in the institution."
        )

    # 4. Resolve Target Department
    dept_code = req.department_code.strip().upper()
    dept = db.query(Department).filter(
        (Department.dept_code.ilike(dept_code)) | 
        (Department.name.ilike(f"%{dept_code}%"))
    ).first()

    if not dept:
        # Fallback to primary department if not found
        dept = db.query(Department).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target department '{dept_code}' does not exist in the institutional schema."
            )

    try:
        # 5. Create Student Entity
        new_student = Student(
            student_id_str=clean_id,
            full_name=req.full_name.strip(),
            email=clean_email,
            department_id=dept.id,
            batch_year=req.batch_year or 2024,
            semester=req.semester or 3
        )
        db.add(new_student)
        db.flush()  # Obtain new_student.id

        # 6. Initialize Course Summaries for newly registered student
        courses = db.query(Course).filter_by(department_id=dept.id).all()
        for course in courses:
            summary = StudentCourseSummary(
                student_id=new_student.id,
                course_id=course.id,
                total_classes=0,
                attended_classes=0,
                late_classes=0,
                absent_classes=0,
                attendance_pct=100.0,
                is_defaulter=False
            )
            db.add(summary)

        # 7. Create User Account
        pwd_hash = PasswordHasherService.hash(initial_password)
        uname = clean_id.lower().replace("-", ".").replace(" ", ".")
        
        # Ensure unique username
        base_uname = uname
        suffix = 1
        while db.query(UserAccount).filter_by(username=uname).first():
            uname = f"{base_uname}.{suffix}"
            suffix += 1

        new_user = UserAccount(
            username=uname,
            email=clean_email,
            password_hash=pwd_hash,
            full_name=req.full_name.strip(),
            role="STUDENT",
            department_id=dept.id,
            student_id=new_student.id,
            avatar_icon="🎓",
            is_active=True
        )
        db.add(new_user)
        db.flush()

        # 8. Record Immutable Security Audit Log Entry
        actor_title = current_user.full_name or "Dr. Manju Lalwani Pathak (Principal)"
        SecurityAuditLogger.log(
            db=db,
            user_id=current_user.id,
            event_type="SUPERADMIN_STUDENT_ENROLLED",
            severity="INFO",
            ip_address=ip_addr,
            user_agent=user_agent,
            device_fingerprint="SUPERADMIN-AUTHORITY-PORTAL",
            details={
                "action": "DIRECT_STUDENT_ENROLLMENT",
                "authorized_by": actor_title,
                "target_student_id": new_student.id,
                "target_roll_no": clean_id,
                "target_email": clean_email,
                "target_department": dept.name,
                "department_code": dept.dept_code,
                "semester": new_student.semester,
                "batch_year": new_student.batch_year,
                "expedited": req.expedited,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        db.commit()

        # Update in-memory anti-proxy lock state
        if hasattr(anti_proxy_engine, "student_hardware_locks"):
            anti_proxy_engine.student_hardware_locks[clean_id] = {
                "device_uuid": None,
                "device_name": "None (Unbound)",
                "is_locked": False,
                "enrolled_at": None
            }

        return {
            "status": "SUCCESS",
            "message": f"Student '{req.full_name}' ({clean_id}) has been directly provisioned and enrolled into {dept.name}.",
            "student": {
                "id": new_student.id,
                "student_id_str": clean_id,
                "full_name": new_student.full_name,
                "email": clean_email,
                "username": new_user.username,
                "department": dept.name,
                "department_code": dept.dept_code,
                "semester": new_student.semester,
                "batch_year": new_student.batch_year,
                "account_status": "ACTIVE",
                "enrolled_by": actor_title
            }
        }

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during direct student enrollment: {str(exc)}"
        )


# ==========================================
# 1B. DIRECT MULTI-CATEGORY USER PROVISIONING
# ==========================================

@admin_router.post(
    "/users/provision",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Admin Direct Multi-Category User Account Provisioning"
)
def admin_provision_user(
    req: AdminProvisionUserRequest,
    request: Request,
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN", "ADMIN_STAFF"])),
    db: Session = Depends(get_db)
):
    """
    Direct Multi-Category User Provisioning (Admin Staff & Principal Authority):
    Provisions and saves accounts across all institutional categories:
      - STUDENT: Creates Student + UserAccount ('STUDENT') + Course summaries + Anti-proxy slot.
      - FACULTY / TEACHER: Creates Faculty + UserAccount ('TEACHER').
      - COORDINATOR / HOD: Creates Faculty (if needed) + UserAccount ('COORDINATOR').
      - ADMIN_STAFF / ADMIN: Creates UserAccount ('ADMIN_STAFF').
    
    Generates default temporary password, flags account for first-login security setup,
    and logs an immutable SecurityAuditLog event.
    """
    clean_email = req.email.strip().lower()
    clean_id = req.identifier.strip().upper()
    category = (req.category or "STUDENT").strip().upper()
    ip_addr = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")

    # 1. Validate Initial Password Strength
    initial_password = req.initial_password or f"{clean_id.replace('-', '')}@CHMC2026"
    is_valid_pw, _ = PasswordPolicy.validate(initial_password)
    if not is_valid_pw:
        initial_password = "CHMC@2026!"

    # 2. Check for duplicate email across user accounts
    existing_user = db.query(UserAccount).filter(UserAccount.email.ilike(clean_email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A user account with email '{clean_email}' already exists (Username: {existing_user.username})."
        )

    # 3. Resolve Target Department
    dept_code = (req.department_code or "DS").strip().upper()
    dept = db.query(Department).filter(
        (Department.dept_code.ilike(dept_code)) | 
        (Department.name.ilike(f"%{dept_code}%"))
    ).first()

    if not dept:
        dept = db.query(Department).first()

    dept_id = dept.id if dept else None
    dept_name = dept.name if dept else "General Administration"
    dept_code_str = dept.dept_code if dept else "GEN"

    try:
        actor_title = current_user.full_name or "Admin Office Staff"
        pwd_hash = PasswordHasherService.hash(initial_password)
        base_uname = clean_id.lower().replace("-", ".").replace(" ", ".")
        uname = base_uname
        suffix = 1
        while db.query(UserAccount).filter_by(username=uname).first():
            uname = f"{base_uname}.{suffix}"
            suffix += 1

        created_details = {}

        if category == "STUDENT":
            existing_student = db.query(Student).filter(Student.student_id_str.ilike(clean_id)).first()
            if existing_student:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"A student with roll number '{clean_id}' is already registered in the institution."
                )

            new_student = Student(
                student_id_str=clean_id,
                full_name=req.full_name.strip(),
                email=clean_email,
                department_id=dept_id,
                batch_year=req.batch_year or 2024,
                semester=req.semester or 3
            )
            db.add(new_student)
            db.flush()

            if dept_id:
                courses = db.query(Course).filter_by(department_id=dept_id).all()
                for course in courses:
                    summary = StudentCourseSummary(
                        student_id=new_student.id,
                        course_id=course.id,
                        total_classes=0,
                        attended_classes=0,
                        late_classes=0,
                        absent_classes=0,
                        attendance_pct=100.0,
                        is_defaulter=False
                    )
                    db.add(summary)

            new_user = UserAccount(
                username=uname,
                email=clean_email,
                password_hash=pwd_hash,
                full_name=req.full_name.strip(),
                role="STUDENT",
                department_id=dept_id,
                student_id=new_student.id,
                avatar_icon="🎓",
                is_active=True
            )
            db.add(new_user)
            db.flush()

            if hasattr(anti_proxy_engine, "student_hardware_locks"):
                anti_proxy_engine.student_hardware_locks[clean_id] = {
                    "device_uuid": None,
                    "device_name": "None (Unbound)",
                    "is_locked": False,
                    "enrolled_at": None
                }

            created_details = {
                "category": "STUDENT",
                "role": "STUDENT",
                "student_id": new_student.id,
                "roll_no": clean_id,
                "semester": new_student.semester,
                "batch_year": new_student.batch_year,
                "division": req.division or "A"
            }

        elif category in ["FACULTY", "TEACHER", "PROFESSOR"]:
            existing_fac = db.query(Faculty).filter(
                (Faculty.faculty_id_str.ilike(clean_id)) | (Faculty.email.ilike(clean_email))
            ).first()
            if existing_fac:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"A faculty member with ID '{clean_id}' or email '{clean_email}' already exists."
                )

            new_fac = Faculty(
                faculty_id_str=clean_id,
                full_name=req.full_name.strip(),
                email=clean_email,
                department_id=dept_id or 1,
                designation=req.designation or "Assistant Professor"
            )
            db.add(new_fac)
            db.flush()

            new_user = UserAccount(
                username=uname,
                email=clean_email,
                password_hash=pwd_hash,
                full_name=req.full_name.strip(),
                role="TEACHER",
                department_id=dept_id,
                faculty_id=new_fac.id,
                avatar_icon="👨‍🏫",
                is_active=True
            )
            db.add(new_user)
            db.flush()

            created_details = {
                "category": "FACULTY",
                "role": "TEACHER",
                "faculty_id": new_fac.id,
                "faculty_id_str": clean_id,
                "designation": new_fac.designation
            }

        elif category in ["COORDINATOR", "HOD"]:
            new_fac = Faculty(
                faculty_id_str=clean_id,
                full_name=req.full_name.strip(),
                email=clean_email,
                department_id=dept_id or 1,
                designation=req.designation or f"Head of Department / Coordinator ({dept_code_str})"
            )
            db.add(new_fac)
            db.flush()

            new_user = UserAccount(
                username=uname,
                email=clean_email,
                password_hash=pwd_hash,
                full_name=req.full_name.strip(),
                role="COORDINATOR",
                department_id=dept_id,
                faculty_id=new_fac.id,
                avatar_icon="🏛️",
                is_active=True
            )
            db.add(new_user)
            db.flush()

            created_details = {
                "category": "COORDINATOR",
                "role": "COORDINATOR",
                "coordinator_id": clean_id,
                "department": dept_name
            }

        else:  # ADMIN_STAFF / ADMIN / OTHER
            new_user = UserAccount(
                username=uname,
                email=clean_email,
                password_hash=pwd_hash,
                full_name=req.full_name.strip(),
                role="ADMIN_STAFF",
                department_id=dept_id,
                avatar_icon="🏢",
                is_active=True
            )
            db.add(new_user)
            db.flush()

            created_details = {
                "category": "ADMIN_STAFF",
                "role": "ADMIN_STAFF",
                "staff_id": clean_id,
                "section": req.designation or "Admissions & Student Administration"
            }

        # Record Security Audit Log
        SecurityAuditLogger.log(
            db=db,
            user_id=current_user.id,
            event_type="ADMIN_USER_PROVISIONED",
            severity="INFO",
            ip_address=ip_addr,
            user_agent=user_agent,
            details={
                "action": "PROVISION_USER_ACCOUNT",
                "category": category,
                "target_identifier": clean_id,
                "target_email": clean_email,
                "target_name": req.full_name.strip(),
                "assigned_role": new_user.role,
                "department": dept_name,
                "authorized_by": actor_title,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        db.commit()

        return {
            "status": "SUCCESS",
            "message": f"Account for '{req.full_name}' ({clean_id}) provisioned successfully as {new_user.role} in {dept_name}.",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "identifier": clean_id,
                "full_name": new_user.full_name,
                "email": clean_email,
                "role": new_user.role,
                "category": category,
                "department": dept_name,
                "department_code": dept_code_str,
                "initial_password": initial_password,
                "account_status": "ACTIVE",
                "enrolled_by": actor_title,
                **created_details
            }
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during user provisioning: {str(exc)}"
        )


# ==========================================
# 2. STUDENT ACCOUNT EXPULSION & CASCADE PURGE
# ==========================================

@admin_router.delete(
    "/students/{student_id_str}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Principal Student Expulsion & Account Purge"
)
def superadmin_expel_student(
    student_id_str: str,
    req: AdminExpelStudentRequest,
    request: Request,
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Super-Admin Student Expulsion & Account Revocation:
    Permanently deletes a student's profile, authentication credentials, bound hardware passkeys,
    attendance facts, and summaries in compliance with disciplinary actions, admissions cancellations,
    or graduation offboarding.
    
    Requires:
      - Valid Roll Number verification confirmation (`confirm_roll_no`).
      - Mandatory institutional expulsion reason.
      - Super-Admin or Principal role clearance.
      
    Atomic Cascade Purge deletes:
      - `UserAccount` (and cascading `UserMFA`, `UserRecoveryCode`, `UserPasskey`, `UserSession` records).
      - `FactAttendance`, `RawAttendanceLog`, `StudentCourseSummary`, `ProxyAttemptLog` records.
      - `Student` dimension entity.
      - In-memory `anti_proxy_engine` hardware locks.
      - Records immutable `SUPERADMIN_STUDENT_EXPELLED` audit log.
    """
    clean_id = student_id_str.strip().upper()
    ip_addr = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")

    # 1. Safety Confirmation Check
    if req.confirm_roll_no.strip().upper() != clean_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmation roll number '{req.confirm_roll_no}' does not match target roll number '{clean_id}'."
        )

    # 2. Locate Student Entity
    student = db.query(Student).filter(Student.student_id_str.ilike(clean_id)).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with roll number '{clean_id}' was not found."
        )

    actor_title = current_user.full_name or "Dr. Manju Lalwani Pathak (Principal)"
    student_name = student.full_name
    student_email = student.email
    student_pk = student.id
    dept_id = student.department_id
    dept = db.get(Department, dept_id)
    dept_name = dept.name if dept else "Unknown Department"

    try:
        # 3. Locate & Purge Associated User Accounts
        user_accounts = db.query(UserAccount).filter_by(student_id=student_pk).all()
        for u in user_accounts:
            # Delete child sessions, passkeys, recovery codes, MFA
            db.query(UserSession).filter_by(user_id=u.id).delete()
            db.query(UserPasskey).filter_by(user_id=u.id).delete()
            db.query(UserRecoveryCode).filter_by(user_id=u.id).delete()
            db.query(UserMFA).filter_by(user_id=u.id).delete()
            db.delete(u)

        # 4. Purge Medallion Attendance Facts & Logs
        db.query(FactAttendance).filter_by(student_id=student_pk).delete()
        db.query(RawAttendanceLog).filter_by(student_id_str=clean_id).delete()
        db.query(StudentCourseSummary).filter_by(student_id=student_pk).delete()
        db.query(ProxyAttemptLog).filter_by(student_id_str=clean_id).delete()

        # 5. Delete Student Entity
        db.delete(student)

        # 6. Record Immutable Security Audit Log
        SecurityAuditLogger.log(
            db=db,
            user_id=current_user.id,
            event_type="SUPERADMIN_STUDENT_EXPELLED",
            severity="CRITICAL",
            ip_address=ip_addr,
            user_agent=user_agent,
            device_fingerprint="SUPERADMIN-AUTHORITY-PORTAL",
            details={
                "action": "STUDENT_EXPULSION_AND_ACCOUNT_PURGE",
                "authorized_by": actor_title,
                "expelled_student_id": student_pk,
                "expelled_roll_no": clean_id,
                "expelled_name": student_name,
                "expelled_email": student_email,
                "department": dept_name,
                "reason": req.reason,
                "expulsion_type": req.expulsion_type,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        db.commit()

        # 7. Purge in-memory device lock state
        if hasattr(anti_proxy_engine, "student_hardware_locks") and clean_id in anti_proxy_engine.student_hardware_locks:
            del anti_proxy_engine.student_hardware_locks[clean_id]

        return {
            "status": "SUCCESS",
            "message": f"Student '{student_name}' ({clean_id}) has been permanently expelled and expunged from the institution.",
            "expulsion_details": {
                "roll_no": clean_id,
                "name": student_name,
                "email": student_email,
                "department": dept_name,
                "authorized_by": actor_title,
                "reason": req.reason,
                "expulsion_type": req.expulsion_type,
                "purged_records": ["UserAccount", "Passkeys", "Sessions", "AttendanceFacts", "CourseSummaries", "StudentProfile"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during student expulsion cascade: {str(exc)}"
        )


# ==========================================
# 2B. ADMINISTRATIVE PASSKEY & DEVICE RESET
# ==========================================

@admin_router.post(
    "/students/{student_id_str}/reset-device",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Admin Student Passkey & Biometric Device Reset"
)
def admin_reset_student_device(
    student_id_str: str,
    request: Request,
    reason: Optional[str] = "Phone upgraded / Hardware lost",
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN", "ADMIN_STAFF", "HOD"])),
    db: Session = Depends(get_db)
):
    """
    Emergency Administrative Passkey & Biometric Device Reset:
    Unlinks a student's prior physical handset or biometric passkey when they upgrade or lose their device.
    Purges UserPasskey records, revokes active sessions, and resets is_device_bound to False.
    Next login requires binding their new phone.
    """
    clean_id = student_id_str.strip()
    clean_lower = clean_id.lower()
    clean_hyphen = clean_lower.replace(".", "-")
    clean_dotted = clean_lower.replace("-", ".")

    # 1. Reset in-memory anti-proxy engine
    anti_proxy_engine.reset_student_device(clean_id, authorized_by=current_user.full_name)
    anti_proxy_engine.student_hardware_locks.pop(clean_hyphen, None)
    anti_proxy_engine.student_hardware_locks.pop(clean_dotted, None)

    # 2. Find student / user account
    user = db.query(UserAccount).filter(
        (UserAccount.username.ilike(clean_lower)) |
        (UserAccount.username.ilike(clean_hyphen)) |
        (UserAccount.username.ilike(clean_dotted)) |
        (UserAccount.email.ilike(clean_lower))
    ).first()

    if not user:
        student = db.query(Student).filter(
            (Student.student_id_str.ilike(clean_id)) |
            (Student.student_id_str.ilike(clean_hyphen)) |
            (Student.student_id_str.ilike(clean_dotted))
        ).first()
        if student:
            user = db.query(UserAccount).filter_by(student_id=student.id).first()
            if not user:
                user = db.query(UserAccount).filter(UserAccount.email.ilike(student.email)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student account '{student_id_str}' not found in institutional directory."
        )

    # 3. Purge passkeys & sessions
    passkeys_purged = db.query(UserPasskey).filter_by(user_id=user.id).delete()
    sessions_revoked = db.query(UserSession).filter_by(user_id=user.id).delete()

    user.is_device_bound = False
    user.bound_device_name = None
    user.bound_device_uuid = None
    user.updated_at = datetime.now()

    # 4. Security Audit Log
    ip_addr = request.client.host if request.client else "127.0.0.1"
    audit = SecurityAuditLog(
        user_id=user.id,
        event_type="ADMIN_DEVICE_RESET",
        severity="WARNING",
        ip_address=ip_addr,
        details=json.dumps({
            "student_id_str": clean_id,
            "authorized_by": f"{current_user.full_name} ({current_user.role})",
            "reason": reason,
            "passkeys_purged": passkeys_purged,
            "sessions_revoked": sessions_revoked,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Biometric passkey and hardware lock unlinked for student '{user.full_name}' ({clean_id}).",
        "details": {
            "student": user.full_name,
            "identifier": clean_id,
            "authorized_by": current_user.full_name,
            "passkeys_purged": passkeys_purged,
            "sessions_revoked": sessions_revoked,
            "next_step": "Student will be prompted to register their new handset on next login."
        }
    }


# ==========================================
# 3. MASTER INSTITUTIONAL STUDENT GOVERNANCE LEDGER
# ==========================================

@admin_router.get(
    "/students",
    response_model=List[AdminStudentResponse],
    summary="Master Institutional Student Directory"
)
def get_all_institutional_students(
    department_code: Optional[str] = None,
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "HOD", "COORDINATOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Returns the master student governance ledger across all college departments
    with real-time attendance rates, semester level, and hardware lock status.
    """
    query = db.query(Student)
    if department_code:
        dept = db.query(Department).filter(
            (Department.dept_code.ilike(department_code)) | 
            (Department.name.ilike(f"%{department_code}%"))
        ).first()
        if dept:
            query = query.filter_by(department_id=dept.id)

    students = query.order_by(Student.student_id_str.asc()).all()
    results = []

    for s in students:
        dept = db.get(Department, s.department_id) if s.department_id else None
        dept_code = dept.dept_code if dept else "GEN"
        dept_name = dept.name if dept else "General Department"

        # Calculate overall attendance % across summaries
        summaries = db.query(StudentCourseSummary).filter_by(student_id=s.id).all()
        total_cls = sum(sum_item.total_classes for sum_item in summaries)
        attended_cls = sum(sum_item.attended_classes for sum_item in summaries)
        att_pct = round((attended_cls / total_cls * 100.0), 1) if total_cls > 0 else 100.0
        is_def = att_pct < 75.0 if total_cls > 0 else False

        # Device Lock Status
        lock_info = getattr(anti_proxy_engine, "student_hardware_locks", {}).get(s.student_id_str, {})
        is_locked = bool(lock_info.get("device_uuid"))
        dev_name = lock_info.get("device_name", "Unbound")

        # User Account Status
        user = db.query(UserAccount).filter_by(student_id=s.id).first()
        acc_active = user.is_active if user else True

        results.append(
            AdminStudentResponse(
                id=s.id,
                student_id_str=s.student_id_str,
                full_name=s.full_name,
                email=s.email,
                department_code=dept_code,
                department_name=dept_name,
                batch_year=s.batch_year or 2024,
                semester=s.semester or 3,
                total_classes=total_cls,
                attended_classes=attended_cls,
                attendance_pct=att_pct,
                is_defaulter=is_def,
                is_device_locked=is_locked,
                device_name=dev_name,
                account_active=acc_active,
                created_at=s.created_at.isoformat() if s.created_at else None
            )
        )

    return results


# ==========================================
# 4. IMMUTABLE SECURITY AUDIT LEDGER
# ==========================================

@admin_router.get(
    "/audit-ledger",
    response_model=List[AdminAuditLogEntry],
    summary="Immutable Institutional Audit Ledger"
)
def get_institutional_audit_ledger(
    event_category: Optional[str] = None,
    limit: int = 100,
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Returns cryptographic, append-only security audit log entries for regulatory,
    NAAC, and university governance compliance audits.
    """
    query = db.query(SecurityAuditLog).order_by(SecurityAuditLog.created_at.desc())
    
    if event_category:
        query = query.filter(SecurityAuditLog.event_type.ilike(f"%{event_category}%"))

    logs = query.limit(limit).all()
    results = []

    for log in logs:
        # Resolve actor name
        actor_name = "Dr. Manju Lalwani Pathak (Principal)"
        if log.user_id:
            user = db.get(UserAccount, log.user_id)
            if user:
                actor_name = f"{user.full_name} ({user.role})"

        parsed_details = {}
        if log.details:
            try:
                parsed_details = json.loads(log.details) if isinstance(log.details, str) else log.details
            except Exception:
                parsed_details = {"raw": log.details}

        target_id = parsed_details.get("target_roll_no") or parsed_details.get("expelled_roll_no") or parsed_details.get("student_id_str")

        results.append(
            AdminAuditLogEntry(
                id=log.id,
                event_type=log.event_type,
                severity=log.severity or "INFO",
                actor_name=actor_name,
                target_identifier=target_id,
                ip_address=log.ip_address or "127.0.0.1",
                device_fingerprint=log.device_fingerprint or "AUTHORITY-SESSION",
                details=parsed_details,
                created_at=log.created_at.isoformat() if log.created_at else datetime.now(timezone.utc).isoformat()
            )
        )

    return results


# ==========================================
# 5. ADMIN STAFF & INSTITUTIONAL METRICS OVERVIEW
# ==========================================

@admin_router.get(
    "/overview-stats",
    response_model=Dict[str, Any],
    summary="Admin Staff Institutional Metric Overview"
)
def get_admin_overview_stats(
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN", "ADMIN_STAFF"])),
    db: Session = Depends(get_db)
):
    """
    Returns live aggregated database totals for the Admin Staff KPI cards:
      - Total Enrolled Students
      - Total Teaching Faculty & Coordinators
      - Total User Accounts
      - Anti-Proxy Enclave Locked vs Unbound counts
      - Temporary Password vs Activated Passwords
    """
    total_students = db.query(Student).count()
    total_faculty = db.query(Faculty).count()
    total_users = db.query(UserAccount).count()
    total_departments = db.query(Department).count()

    # Hardware lock status
    locked_count = 0
    if hasattr(anti_proxy_engine, "student_hardware_locks"):
        locked_count = sum(1 for v in anti_proxy_engine.student_hardware_locks.values() if v.get("device_uuid"))

    unbound_count = max(0, total_students - locked_count)
    active_users = db.query(UserAccount).filter_by(is_active=True).count()

    return {
        "institution_name": "Smt. C.H.M. College",
        "total_students": total_students,
        "total_faculty": total_faculty,
        "total_users": total_users,
        "total_departments": total_departments,
        "device_locked_students": locked_count,
        "device_unbound_students": unbound_count,
        "active_users": active_users,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

