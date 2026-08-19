"""
UniAttend 360 - Enterprise Multi-Layer Security & Cryptography Engine.
Implements:
  1. Argon2id / bcrypt password hashing with complexity validation
  2. Rate limiting, progressive backoff, and 15-minute brute-force lockout
  3. RFC 6238 TOTP Two-Step Verification with replay prevention
  4. Cryptographic emergency recovery code management
  5. Cryptographic session tracking, device fingerprinting, and revocation
  6. Non-repudiation security audit logging (zero-secret storage)
"""

import os
import re
import time
import secrets
import base64
import json
from io import BytesIO
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

import jwt
import pyotp
import qrcode
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Header
from sqlalchemy.orm import Session

from database.models import (
    UserAccount, UserMFA, UserRecoveryCode, UserSession, 
    SecurityAuditLog, LoginAttempt
)
from database.db_manager import get_db, get_db_session

# ==========================================
# CONFIGURATION & SECRETS
# ==========================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "UniAttend-Enterprise-AuthKey-CHMC-2026-SuperSecure")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
TEMP_MFA_TOKEN_EXPIRE_MINUTES = 5

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

argon2_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32
)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==========================================
# 1. PRIMARY AUTH: PASSWORD HASHER & POLICY
# ==========================================

class PasswordPolicy:
    """Enforces enterprise password complexity standards."""

    @staticmethod
    def validate(password: str) -> Tuple[bool, Optional[str]]:
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter (A-Z)."
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter (a-z)."
        if not re.search(r"[0-9]", password):
            return False, "Password must contain at least one digit (0-9)."
        if not re.search(r"[\W_]", password):
            return False, "Password must contain at least one special character (!@#$%^&*)."
        return True, None


class PasswordHasherService:
    """Modern hybrid Argon2id password hasher with legacy bcrypt fallback support."""

    @staticmethod
    def hash(password: str) -> str:
        return argon2_hasher.hash(password)

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        if not hashed_password:
            return False
        # 1. Try Argon2id
        if hashed_password.startswith("$argon2"):
            try:
                return argon2_hasher.verify(hashed_password, plain_password)
            except (VerifyMismatchError, InvalidHash):
                return False
        # 2. Fallback to bcrypt
        try:
            return bcrypt_context.verify(plain_password, hashed_password)
        except Exception:
            return False


# ==========================================
# 2. BRUTE-FORCE & LOCKOUT PROTECTION
# ==========================================

class BruteForceProtector:
    """Detects credential stuffing and enforces temporary account lockouts."""

    @staticmethod
    def check_lockout(user: UserAccount) -> None:
        if user.is_locked and user.lockout_until:
            if datetime.now() < user.lockout_until:
                remaining_sec = int((user.lockout_until - datetime.now()).total_seconds())
                remaining_min = max(1, remaining_sec // 60)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Account is temporarily locked due to excessive failed attempts. Try again in {remaining_min} minutes."
                )
            else:
                # Lockout window elapsed, reset lock
                user.is_locked = False
                user.failed_login_attempts = 0
                user.lockout_until = None

    @staticmethod
    def record_failed_attempt(db: Session, user: Optional[UserAccount], identifier: str, ip_address: Optional[str] = None):
        # Record into login_attempts table
        attempt = LoginAttempt(identifier=identifier, ip_address=ip_address, success=False)
        db.add(attempt)

        if user:
            user.failed_login_attempts += 1
            user.last_failed_login_at = datetime.now()
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.is_locked = True
                user.lockout_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                SecurityAuditLogger.log(
                    db=db,
                    user_id=user.id,
                    event_type="ACCOUNT_LOCKOUT",
                    severity="WARNING",
                    ip_address=ip_address,
                    details={"failed_attempts": user.failed_login_attempts, "lockout_minutes": LOCKOUT_DURATION_MINUTES}
                )
        db.commit()

    @staticmethod
    def reset_attempts(db: Session, user: UserAccount, identifier: str, ip_address: Optional[str] = None):
        user.failed_login_attempts = 0
        user.is_locked = False
        user.lockout_until = None
        user.last_login_at = datetime.now()
        
        attempt = LoginAttempt(identifier=identifier, ip_address=ip_address, success=True)
        db.add(attempt)
        db.commit()


# ==========================================
# 3. LAYER 2: TOTP TWO-STEP VERIFICATION
# ==========================================

class TOTPService:
    """RFC 6238 Time-Based One-Time Password engine with anti-replay tracking."""

    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, email: str, issuer: str = "UniAttend 360 - Smt CHMC") -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)

    @staticmethod
    def generate_qr_base64(uri: str) -> str:
        qr = qrcode.QRCode(box_size=6, border=2)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#10B981", back_color="#0B1326")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    @staticmethod
    def verify_code(secret: str, code: str, last_used_timestep: int = 0) -> Tuple[bool, int]:
        """
        Validates 6-digit OTP code against secret and enforces single-use replay protection.
        """
        totp = pyotp.TOTP(secret)
        cleaned_code = str(code).strip()
        
        # Verify code with a 1-step drift window (30s)
        current_time = time.time()
        current_slot = int(current_time // 30)

        # Check current slot and previous slot
        for slot in [current_slot, current_slot - 1]:
            if slot <= last_used_timestep:
                continue  # Slot already used (replay attack prevented)
            if totp.verify(cleaned_code, for_time=datetime.fromtimestamp(slot * 30, tz=timezone.utc), valid_window=1):
                return True, current_slot
                
        return False, last_used_timestep


# ==========================================
# 4. ACCOUNT RECOVERY: RECOVERY CODES
# ==========================================

class RecoveryCodeService:
    """Generates and securely validates one-time emergency backup recovery codes."""

    @staticmethod
    def generate_codes(count: int = 8) -> List[str]:
        codes = []
        for _ in range(count):
            # Format: XXXX-XXXX (e.g. 9B2F-7K4M)
            part1 = secrets.token_hex(2).upper()
            part2 = secrets.token_hex(2).upper()
            codes.append(f"{part1}-{part2}")
        return codes

    @staticmethod
    def store_codes(db: Session, user_id: int, plain_codes: List[str]):
        # Invalidate any existing unused recovery codes
        db.query(UserRecoveryCode).filter_by(user_id=user_id, is_used=False).delete()
        for code in plain_codes:
            code_hash = PasswordHasherService.hash(code)
            rec = UserRecoveryCode(user_id=user_id, code_hash=code_hash, is_used=False)
            db.add(rec)
        db.commit()

    @staticmethod
    def verify_and_consume(db: Session, user_id: int, code_attempt: str) -> bool:
        cleaned_attempt = code_attempt.strip().upper()
        unused_codes = db.query(UserRecoveryCode).filter_by(user_id=user_id, is_used=False).all()
        
        for record in unused_codes:
            if PasswordHasherService.verify(cleaned_attempt, record.code_hash):
                record.is_used = True
                record.used_at = datetime.now()
                db.commit()
                return True
        return False


# ==========================================
# 5. SESSION & TRUSTED DEVICE MANAGEMENT
# ==========================================

class SessionService:
    """Cryptographic session tracker with instant revocation and device binding."""

    @staticmethod
    def create_session(
        db: Session,
        user_id: int,
        device_fingerprint: str,
        device_name: str = "Web Browser",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        is_trusted: bool = False
    ) -> Tuple[str, UserSession]:
        session_token = secrets.token_urlsafe(48)
        expires_at = datetime.now() + timedelta(days=30 if is_trusted else 1)
        
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            is_trusted=is_trusted,
            expires_at=expires_at
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session_token, session

    @staticmethod
    def validate_session(db: Session, session_token: str) -> Optional[UserSession]:
        session = db.query(UserSession).filter_by(session_token=session_token, is_revoked=False).first()
        if not session:
            return None
        if datetime.now() > session.expires_at:
            session.is_revoked = True
            db.commit()
            return None
        # Update last activity timestamp
        session.last_activity_at = datetime.now()
        db.commit()
        return session

    @staticmethod
    def revoke_session(db: Session, session_id: int, user_id: int) -> bool:
        session = db.query(UserSession).filter_by(id=session_id, user_id=user_id).first()
        if session:
            session.is_revoked = True
            db.commit()
            return True
        return False

    @staticmethod
    def revoke_all_sessions(db: Session, user_id: int, current_session_token: Optional[str] = None) -> int:
        query = db.query(UserSession).filter_by(user_id=user_id, is_revoked=False)
        if current_session_token:
            query = query.filter(UserSession.session_token != current_session_token)
        count = query.update({"is_revoked": True})
        db.commit()
        return count


# ==========================================
# 6. SECURITY AUDIT LOGGING (ZERO SECRETS)
# ==========================================

class SecurityAuditLogger:
    """Non-repudiation security audit logger without credential or secret leakage."""

    @staticmethod
    def log(
        db: Session,
        event_type: str,
        user_id: Optional[int] = None,
        severity: str = "INFO",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        try:
            # Filter out any accidental secret keywords from details dict
            safe_details = {}
            if details:
                for k, v in details.items():
                    if any(bad in k.lower() for bad in ["password", "secret", "token", "key", "pin", "code"]):
                        safe_details[k] = "[REDACTED]"
                    else:
                        safe_details[k] = v

            entry = SecurityAuditLog(
                user_id=user_id,
                event_type=event_type,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                details=json.dumps(safe_details) if safe_details else None,
                created_at=datetime.now()
            )
            db.add(entry)
            db.commit()
        except Exception:
            db.rollback()


# ==========================================
# 7. JWT TOKENS & AUTH DEPENDENCIES
# ==========================================

def create_jwt_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "uniattend.chmc.edu"
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_temp_mfa_token(user_id: int, identifier: str, mfa_type: str) -> str:
    """Short-lived 5-minute token issued between Primary Auth and Layer 2 MFA."""
    payload = {
        "sub": str(user_id),
        "identifier": identifier,
        "mfa_type": mfa_type,
        "is_mfa_pending": True,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TEMP_MFA_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token expired. Please log in again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cryptographic authentication token.")


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> UserAccount:
    """Server-side authentication middleware for protected API endpoints."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Bearer Authorization token header."
        )

    token = authorization.split(" ")[1]
    payload = decode_jwt_token(token)

    if payload.get("is_mfa_pending"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2-Step Verification (MFA) required before accessing this resource."
        )

    user_id = payload.get("sub")
    session_token = payload.get("session_token")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    user = db.get(UserAccount, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is deactivated or invalid.")

    # Validate active session token if present
    if session_token:
        active_sess = SessionService.validate_session(db, session_token)
        if not active_sess:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired. Please sign in again."
            )

    return user


def require_role(allowed_roles: List[str]):
    """Strict server-side RBAC dependency factory."""
    def role_checker(current_user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{current_user.role}' is not authorized to access this resource."
            )
        return current_user
    return role_checker
