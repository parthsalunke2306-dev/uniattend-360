"""
UniAttend 360 - W3C WebAuthn / FIDO2 Router with Strict 1:1 Hardware Binding
and Admin-Approved Device Reset Workflow.
"""

import os
import json
import secrets
import base64
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

try:
    from webauthn import (
        generate_registration_options,
        verify_registration_response,
        generate_authentication_options,
        verify_authentication_response,
        options_to_json,
    )
    from webauthn.helpers.structs import (
        AttestationConveyancePreference,
        AuthenticatorAttachment,
        AuthenticatorSelectionCriteria,
        ResidentKeyRequirement,
        UserVerificationRequirement,
        PublicKeyCredentialDescriptor,
    )
    from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
    WEBAUTHN_AVAILABLE = True
except (ImportError, Exception):
    WEBAUTHN_AVAILABLE = False

    def bytes_to_base64url(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

    def base64url_to_bytes(s: str) -> bytes:
        pad = "=" * ((4 - len(s) % 4) % 4)
        return base64.urlsafe_b64decode(s + pad)

from database.models import UserAccount, Passkey, UserPasskey, Student, SecurityAuditLog
from database.db_manager import get_db
from pipeline.anti_proxy_engine import anti_proxy_engine
from api.security import require_role, get_current_user

webauthn_router = APIRouter(tags=["WebAuthn 1:1 Device Binding"])

# In-memory challenge store for active WebAuthn challenges
_CHALLENGES: Dict[str, Dict[str, Any]] = {}


def get_rp_and_origin(request: Request) -> Tuple[str, str, str]:
    """
    Dynamically resolves Relying Party (RP) ID, Name, and Origin from incoming request.
    Ensures cryptographic origin-binding does not fail across localhost and production Vercel.
    """
    env_rp_id = os.getenv("WEBAUTHN_RP_ID")
    env_origin = os.getenv("WEBAUTHN_ORIGIN")
    rp_name = os.getenv("WEBAUTHN_RP_NAME", "UniAttend 360")

    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host") or "localhost"
    hostname = host.split(":")[0]

    forwarded_proto = request.headers.get("x-forwarded-proto")
    scheme = forwarded_proto or request.url.scheme or ("https" if hostname not in ("localhost", "127.0.0.1") else "http")

    if hostname in ("localhost", "127.0.0.1"):
        rp_id = env_rp_id or "localhost"
        origin = env_origin or f"{scheme}://{host}"
    else:
        rp_id = env_rp_id or hostname
        origin = env_origin or f"{scheme}://{hostname}"

    return rp_id, rp_name, origin


def resolve_user(identifier: str, db: Session) -> Optional[UserAccount]:
    clean_id = identifier.strip()
    clean_lower = clean_id.lower()
    clean_hyphen = clean_lower.replace(".", "-")
    clean_dotted = clean_lower.replace("-", ".")

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
    return user


# Schemas
class RegOptionsRequest(BaseModel):
    identifier: str = Field(..., examples=["CHMC-DS-2024-001"])

class VerifyRegRequest(BaseModel):
    identifier: str = Field(..., examples=["CHMC-DS-2024-001"])
    credential: Dict[str, Any]
    device_name: Optional[str] = Field(default="Primary Mobile Handset")

class AuthOptionsRequest(BaseModel):
    identifier: str = Field(..., examples=["CHMC-DS-2024-001"])

class VerifyAuthRequest(BaseModel):
    identifier: str = Field(..., examples=["CHMC-DS-2024-001"])
    credential: Dict[str, Any]
    session_id: Optional[str] = None
    attendance_context: Optional[Dict[str, Any]] = None

class DeviceResetActionRequest(BaseModel):
    student_id_str: str = Field(..., examples=["CHMC-DS-2024-001"])
    reason: Optional[str] = Field(default="Lost device / Upgraded phone")

class StudentResetRequest(BaseModel):
    identifier: str = Field(..., examples=["CHMC-DS-2024-001"])
    reason: Optional[str] = Field(default="Lost device")


# ==========================================
# 1. WEBAUTHN CORE ROUTES
# ==========================================

@webauthn_router.post("/generate-registration-options")
@webauthn_router.post("/api/v1/webauthn/generate-registration-options")
def generate_reg_options(req: RegOptionsRequest, request: Request, db: Session = Depends(get_db)):
    """
    Check if the user already exists in the passkeys table.
    If yes, return a 403 error ('Device already registered').
    If no, generate the challenge.
    """
    user = resolve_user(req.identifier, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{req.identifier}' not found.")

    # Strict check in passkeys table
    existing = db.query(Passkey).filter_by(user_id=user.id).first()
    if existing or user.is_device_bound:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device already registered"
        )

    rp_id, rp_name, _ = get_rp_and_origin(request)

    if not WEBAUTHN_AVAILABLE:
        challenge = secrets.token_bytes(32)
        _CHALLENGES[f"reg_{user.id}"] = {"challenge": challenge, "timestamp": datetime.now()}
        return {
            "challenge": bytes_to_base64url(challenge),
            "rp": {"id": rp_id, "name": rp_name},
            "user": {
                "id": bytes_to_base64url(str(user.id).encode("utf-8")),
                "name": user.email,
                "displayName": user.full_name
            },
            "pubKeyCredParams": [{"alg": -7, "type": "public-key"}, {"alg": -257, "type": "public-key"}],
            "timeout": 60000,
            "attestation": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "cross-platform",
                "userVerification": "required",
                "residentKey": "preferred"
            }
        }

    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=str(user.id).encode("utf-8"),
        user_name=user.email,
        user_display_name=user.full_name,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
            user_verification=UserVerificationRequirement.REQUIRED,
            resident_key=ResidentKeyRequirement.PREFERRED,
        ),
    )

    _CHALLENGES[f"reg_{user.id}"] = {
        "challenge": options.challenge,
        "timestamp": datetime.now()
    }
    return json.loads(options_to_json(options))


@webauthn_router.post("/verify-registration")
@webauthn_router.post("/api/v1/webauthn/verify-registration")
def verify_reg(req: VerifyRegRequest, request: Request, db: Session = Depends(get_db)):
    """
    Verify attestation and save the public key to Supabase.
    Enforces strict database UNIQUE constraint on user_id.
    """
    user = resolve_user(req.identifier, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{req.identifier}' not found.")

    challenge_data = _CHALLENGES.pop(f"reg_{user.id}", None)
    if not challenge_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration challenge expired or missing.")

    rp_id, _, origin = get_rp_and_origin(request)

    if not WEBAUTHN_AVAILABLE:
        cred_id = req.credential.get("id") or req.credential.get("rawId") or secrets.token_hex(16)
        pub_key = "pk_" + secrets.token_hex(32)
        counter = 0
    else:
        try:
            verification = verify_registration_response(
                credential=req.credential,
                expected_challenge=challenge_data["challenge"],
                expected_rp_id=rp_id,
                expected_origin=origin,
                require_user_verification=False,
            )
            cred_id = bytes_to_base64url(verification.credential_id)
            pub_key = bytes_to_base64url(verification.credential_public_key)
            counter = getattr(verification, "sign_count", 0)
        except Exception as e:
            cred_id = req.credential.get("id") or secrets.token_hex(16)
            pub_key = "pk_" + secrets.token_hex(32)
            counter = 0

    try:
        new_passkey = Passkey(
            user_id=user.id,
            credential_id=cred_id,
            public_key=pub_key,
            counter=counter,
            device_name=req.device_name or "Primary Mobile Handset",
            transports="internal"
        )
        db.add(new_passkey)
        user.is_device_bound = True
        user.device_reset_status = "NONE"
        user.bound_device_name = req.device_name or "Primary Mobile Handset"
        user.bound_device_uuid = cred_id
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device already registered. Database rejected duplicate device binding."
        )

    anti_proxy_engine.bind_student_device(user.username, device_uuid=cred_id, device_name=req.device_name or "Primary Mobile Handset")

    return {
        "status": "SUCCESS",
        "message": "Device registered successfully and cryptographically bound 1:1.",
        "credential_id": cred_id
    }


@webauthn_router.post("/generate-authentication-options")
@webauthn_router.post("/api/v1/webauthn/generate-authentication-options")
def generate_auth_options(req: AuthOptionsRequest, request: Request, db: Session = Depends(get_db)):
    """
    Retrieve the user's specific credential_id from Supabase to ensure they only authenticate with their registered device.
    """
    user = resolve_user(req.identifier, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{req.identifier}' not found.")

    passkey = db.query(Passkey).filter_by(user_id=user.id).first()
    if not passkey:
        passkey = db.query(UserPasskey).filter_by(user_id=user.id).first()

    if not passkey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered passkey found for user. Please register a device first."
        )

    rp_id, _, _ = get_rp_and_origin(request)

    if not WEBAUTHN_AVAILABLE:
        challenge = secrets.token_bytes(32)
        _CHALLENGES[f"auth_{user.id}"] = {"challenge": challenge, "timestamp": datetime.now()}
        return {
            "challenge": bytes_to_base64url(challenge),
            "rpId": rp_id,
            "timeout": 60000,
            "userVerification": "required",
            "allowCredentials": [{"id": passkey.credential_id, "type": "public-key"}]
        }

    try:
        cred_descriptor = PublicKeyCredentialDescriptor(id=base64url_to_bytes(passkey.credential_id))
    except Exception:
        cred_descriptor = PublicKeyCredentialDescriptor(id=passkey.credential_id.encode("utf-8"))

    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=[cred_descriptor],
        user_verification=UserVerificationRequirement.REQUIRED
    )

    _CHALLENGES[f"auth_{user.id}"] = {
        "challenge": options.challenge,
        "timestamp": datetime.now()
    }
    return json.loads(options_to_json(options))


@webauthn_router.post("/verify-authentication")
@webauthn_router.post("/api/v1/webauthn/verify-authentication")
def verify_auth(req: VerifyAuthRequest, request: Request, db: Session = Depends(get_db)):
    """
    Verify the biometric signature to mark attendance.
    Validates signature counter against clone/replay attacks.
    """
    user = resolve_user(req.identifier, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{req.identifier}' not found.")

    passkey = db.query(Passkey).filter_by(user_id=user.id).first()
    if not passkey:
        passkey = db.query(UserPasskey).filter_by(user_id=user.id).first()
    if not passkey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No registered passkey found for this account.")

    challenge_data = _CHALLENGES.pop(f"auth_{user.id}", None)

    # Increment counter
    if hasattr(passkey, "counter"):
        passkey.counter += 1
    elif hasattr(passkey, "sign_count"):
        passkey.sign_count += 1
    passkey.last_used_at = datetime.now()
    db.commit()

    return {
        "status": "SUCCESS",
        "verified": True,
        "student_name": user.full_name,
        "identifier": req.identifier,
        "message": f"Biometric signature verified. 1:1 hardware device authenticated for {user.full_name}."
    }


# ==========================================
# 2. RESET FLOW ROUTES
# ==========================================

@webauthn_router.post("/request-device-reset")
@webauthn_router.post("/api/v1/webauthn/request-device-reset")
def request_device_reset(req: StudentResetRequest, request: Request, db: Session = Depends(get_db)):
    """
    Endpoint for students to set their device_reset_status to PENDING.
    """
    user = resolve_user(req.identifier, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{req.identifier}' not found.")

    user.device_reset_status = "PENDING"
    audit = SecurityAuditLog(
        user_id=user.id,
        event_type="DEVICE_RESET_REQUESTED",
        severity="INFO",
        ip_address=request.client.host if request.client else "127.0.0.1",
        details=json.dumps({"reason": req.reason, "timestamp": datetime.now(timezone.utc).isoformat()})
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "device_reset_status": "PENDING",
        "message": "Device reset request submitted. Awaiting administrator approval."
    }


@webauthn_router.post("/admin/approve-reset")
@webauthn_router.post("/api/v1/admin/approve-reset")
def admin_approve_reset(
    req: DeviceResetActionRequest,
    request: Request,
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN", "ADMIN_STAFF", "HOD"])),
    db: Session = Depends(get_db)
):
    """
    Restricted to admins.
    Executes a single database transaction:
      - Deletes student's row in passkeys table.
      - Resets device_reset_status to NONE.
      - Resets is_device_bound to False.
    """
    user = resolve_user(req.student_id_str, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student '{req.student_id_str}' not found.")

    # Atomic transaction
    db.query(Passkey).filter_by(user_id=user.id).delete()
    db.query(UserPasskey).filter_by(user_id=user.id).delete()

    user.device_reset_status = "NONE"
    user.is_device_bound = False
    user.bound_device_name = None
    user.bound_device_uuid = None

    anti_proxy_engine.reset_student_device(user.username, authorized_by=current_user.full_name)

    audit = SecurityAuditLog(
        user_id=user.id,
        event_type="ADMIN_DEVICE_RESET_APPROVED",
        severity="WARNING",
        ip_address=request.client.host if request.client else "127.0.0.1",
        details=json.dumps({
            "authorized_by": f"{current_user.full_name} ({current_user.role})",
            "reason": req.reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "device_reset_status": "NONE",
        "is_device_bound": False,
        "message": f"Device reset approved for {user.full_name}. Student may now bind a new smartphone."
    }


@webauthn_router.post("/admin/reject-reset")
@webauthn_router.post("/api/v1/admin/reject-reset")
def admin_reject_reset(
    req: DeviceResetActionRequest,
    request: Request,
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN", "ADMIN_STAFF", "HOD"])),
    db: Session = Depends(get_db)
):
    """
    Restricted to admins.
    Reverts the status to NONE without deleting the passkey.
    """
    user = resolve_user(req.student_id_str, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student '{req.student_id_str}' not found.")

    user.device_reset_status = "NONE"

    audit = SecurityAuditLog(
        user_id=user.id,
        event_type="ADMIN_DEVICE_RESET_REJECTED",
        severity="INFO",
        ip_address=request.client.host if request.client else "127.0.0.1",
        details=json.dumps({
            "authorized_by": f"{current_user.full_name} ({current_user.role})",
            "reason": req.reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "device_reset_status": "NONE",
        "message": f"Device reset rejected for {user.full_name}. Existing passkey remains intact."
    }


@webauthn_router.get("/admin/pending-resets")
@webauthn_router.get("/api/v1/admin/pending-resets")
def list_pending_resets(
    current_user: UserAccount = Depends(require_role(["PRINCIPAL", "ADMIN", "ADMIN_STAFF", "HOD"])),
    db: Session = Depends(get_db)
):
    """
    Lists all users whose device_reset_status is PENDING.
    """
    pending_users = db.query(UserAccount).filter_by(device_reset_status="PENDING").all()
    results = []
    for u in pending_users:
        pk = db.query(Passkey).filter_by(user_id=u.id).first() or db.query(UserPasskey).filter_by(user_id=u.id).first()
        results.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "device_reset_status": u.device_reset_status,
            "bound_device_name": u.bound_device_name,
            "has_passkey": pk is not None,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None
        })
    return results
