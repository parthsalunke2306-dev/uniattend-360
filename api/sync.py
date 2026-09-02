"""
UniAttend 360 - Data Sync Bridge Module.
Provides bidirectional state synchronization between offline client browser cache (localStorage)
and the live Supabase PostgreSQL database:
  1. Synchronizes registered passkeys, device locks, and password updates.
  2. Ingests offline provisioned users (Students, Faculty, Staff) created while disconnected.
  3. Flushes offline institutional audit logs into the master database SecurityAuditLog ledger.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db_manager import get_db
from database.models import UserAccount, Student, Faculty, Department, SecurityAuditLog
from api.security import PasswordHasherService, SecurityAuditLogger

sync_router = APIRouter(prefix="/api/v1/sync", tags=["Data Sync Bridge"])


class ClientSyncPayload(BaseModel):
    profiles: Optional[Dict[str, Any]] = None
    audit_logs: Optional[List[Dict[str, Any]]] = None
    lectures: Optional[List[Dict[str, Any]]] = None
    client_version: Optional[str] = None


@sync_router.post(
    "/client-state",
    summary="Synchronize Client Local State with Database",
    status_code=status.HTTP_200_OK
)
def sync_client_state(
    payload: ClientSyncPayload,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Ingests local client state into Supabase PostgreSQL database:
      - Updates device bindings and password hashes for existing accounts.
      - Provisions newly created users into UserAccount and Student tables.
      - Ingests offline audit trail into SecurityAuditLog table.
    """
    synced_users = []
    synced_logs = []

    # 1. Process User Profiles in chronological order
    if payload.profiles:
        for ident, p in payload.profiles.items():
            if not isinstance(p, dict):
                continue

            clean_id = str(ident).strip()
            clean_lower = clean_id.lower()
            email = (p.get("email") or f"{clean_lower}@chmc.edu").strip().lower()
            clean_hyphen = clean_id.replace(".", "-")
            clean_dots = clean_id.replace("-", ".")

            # Find matching UserAccount in database by username, dotted, hyphenated, or email
            user = db.query(UserAccount).filter(
                (UserAccount.username.ilike(clean_lower)) |
                (UserAccount.username.ilike(clean_dots)) |
                (UserAccount.username.ilike(clean_hyphen)) |
                (UserAccount.email.ilike(email))
            ).first()

            if not user:
                # Also check student roll number or student email mapping
                student = db.query(Student).filter(
                    (Student.student_id_str.ilike(clean_id)) |
                    (Student.student_id_str.ilike(clean_hyphen)) |
                    (Student.student_id_str.ilike(clean_dots)) |
                    (Student.email.ilike(email))
                ).first()
                if student:
                    user = db.query(UserAccount).filter(
                        (UserAccount.student_id == student.id) |
                        (UserAccount.email.ilike(student.email))
                    ).first()

            if user:
                # Synchronize device binding state
                if p.get("is_device_bound") is True:
                    user.is_device_bound = True
                dev_name = p.get("device_name") or p.get("bound_device_name")
                if dev_name:
                    user.bound_device_name = dev_name
                dev_uuid = p.get("device_fingerprint") or p.get("bound_device_uuid")
                if dev_uuid:
                    user.bound_device_uuid = dev_uuid

                # Synchronize password status
                if "must_change_password" in p:
                    user.must_change_password = bool(p["must_change_password"])

                if p.get("password_hash"):
                    user.password_hash = p["password_hash"]
                elif p.get("initial_password") and not user.password_hash:
                    user.password_hash = PasswordHasherService.hash(p["initial_password"])

                synced_users.append(user.username)
            else:
                # Provision new user from offline cache
                role = (p.get("role") or "STUDENT").strip().upper()
                name = p.get("name") or p.get("full_name") or clean_id
                init_pwd = p.get("initial_password") or f"{clean_id.replace('-', '')}@CHMC2026"
                pwd_hash = p.get("password_hash") or PasswordHasherService.hash(init_pwd)

                dept = db.query(Department).first()
                dept_id = dept.id if dept else None

                student_id = None
                if role == "STUDENT":
                    student = db.query(Student).filter(
                        (Student.student_id_str.ilike(clean_id)) |
                        (Student.student_id_str.ilike(clean_hyphen)) |
                        (Student.student_id_str.ilike(clean_dots)) |
                        (Student.email.ilike(email))
                    ).first()
                    if not student:
                        student = Student(
                            student_id_str=clean_hyphen.upper(),
                            full_name=name,
                            email=email,
                            department_id=dept_id,
                            batch_year=p.get("batch_year", 2024),
                            semester=p.get("semester", 1)
                        )
                        db.add(student)
                        db.flush()
                    student_id = student.id

                new_user = UserAccount(
                    username=clean_lower.replace("-", ".").replace(" ", "."),
                    email=email,
                    password_hash=pwd_hash,
                    full_name=name,
                    role=role,
                    student_id=student_id,
                    department_id=dept_id,
                    is_active=True,
                    must_change_password=p.get("must_change_password", False),
                    is_device_bound=p.get("is_device_bound", False),
                    bound_device_name=p.get("device_name") or p.get("bound_device_name"),
                    bound_device_uuid=p.get("device_fingerprint") or p.get("bound_device_uuid")
                )
                db.add(new_user)
                synced_users.append(new_user.username)

    # 2. Ingest offline audit ledger into PostgreSQL SecurityAuditLog
    if payload.audit_logs:
        ip_addr = request.client.host if request.client else "127.0.0.1"
        for log in payload.audit_logs:
            if not isinstance(log, dict):
                continue
            event = log.get("event") or log.get("event_type") or "CLIENT_SYNC_EVENT"
            actor = log.get("actor") or "Client User"
            target = log.get("target") or "System"
            severity = log.get("severity") or "INFO"
            details_str = log.get("details") or ""
            device = log.get("device") or log.get("device_fingerprint")

            SecurityAuditLogger.log(
                db=db,
                event_type=event,
                severity=severity,
                ip_address=ip_addr,
                device_fingerprint=device,
                details={"actor": actor, "target": target, "description": details_str}
            )
            synced_logs.append(event)

    db.commit()

    return {
        "status": "success",
        "synced_users_count": len(synced_users),
        "synced_users": synced_users,
        "synced_logs_count": len(synced_logs)
    }


@sync_router.get(
    "/status",
    summary="Check Database Synchronization Status",
    status_code=status.HTTP_200_OK
)
def get_sync_status(db: Session = Depends(get_db)):
    """Returns real-time sync metrics from Supabase database."""
    user_count = db.query(UserAccount).count()
    student_count = db.query(Student).count()
    audit_count = db.query(SecurityAuditLog).count()
    return {
        "status": "online",
        "database": "connected",
        "total_user_accounts": user_count,
        "total_students": student_count,
        "total_audit_logs": audit_count
    }
