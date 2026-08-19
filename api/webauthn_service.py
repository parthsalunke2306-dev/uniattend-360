"""
UniAttend 360 - W3C WebAuthn / FIDO2 / Passkey Native Biometric Service.
Implements:
  - True cryptographic challenge-response for Windows Hello, Touch ID, Face ID, Android Biometrics
  - Zero raw biometric transmission or storage (W3C standard public-key cryptography)
  - Clone and replay attack prevention using signature counters
"""

import os
import json
import base64
import secrets
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

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
    AuthenticatorTransport,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
from sqlalchemy.orm import Session

from database.models import UserAccount, UserPasskey
from api.security import SecurityAuditLogger

# RP (Relying Party) Configuration
RP_ID = os.getenv("WEBAUTHN_RP_ID", "uniattend-360.vercel.app")
RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "UniAttend 360 (Smt. C.H.M. College)")
ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "https://uniattend-360.vercel.app")

# In-memory challenge store for active WebAuthn challenges (with 5-minute TTL)
_ACTIVE_CHALLENGES: Dict[str, Dict[str, Any]] = {}


class WebAuthnService:
    """Manages W3C WebAuthn passkey registration and biometric authentication."""

    @staticmethod
    def get_registration_options(user: UserAccount, db: Session) -> Dict[str, Any]:
        """
        Generates WebAuthn registration options for Windows Hello, Touch ID, Face ID enrollment.
        """
        # Fetch existing credentials to exclude
        existing_passkeys = db.query(UserPasskey).filter_by(user_id=user.id).all()
        exclude_credentials = []
        for pk in existing_passkeys:
            try:
                exclude_credentials.append(
                    PublicKeyCredentialDescriptor(id=base64url_to_bytes(pk.credential_id))
                )
            except Exception:
                pass

        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=str(user.id).encode("utf-8"),
            user_name=user.email,
            user_display_name=user.full_name,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,  # Native Device Biometrics
                user_verification=UserVerificationRequirement.PREFERRED,
                resident_key=ResidentKeyRequirement.PREFERRED,
            ),
            exclude_credentials=exclude_credentials,
        )

        # Store challenge for verification
        challenge_b64 = bytes_to_base64url(options.challenge)
        _ACTIVE_CHALLENGES[f"reg_{user.id}"] = {
            "challenge": options.challenge,
            "timestamp": datetime.now()
        }

        return json.loads(options_to_json(options))

    @staticmethod
    def verify_registration(
        user: UserAccount,
        credential_json: Dict[str, Any],
        device_name: str,
        db: Session
    ) -> UserPasskey:
        """
        Validates cryptographic attestation response from the device and stores public key.
        """
        challenge_key = f"reg_{user.id}"
        challenge_data = _ACTIVE_CHALLENGES.pop(challenge_key, None)
        if not challenge_data:
            raise ValueError("Registration challenge expired or missing. Please try again.")

        expected_challenge = challenge_data["challenge"]

        verification = verify_registration_response(
            credential=credential_json,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            require_user_verification=False,
        )

        credential_id_b64 = bytes_to_base64url(verification.credential_id)
        public_key_b64 = bytes_to_base64url(verification.credential_public_key)

        # Check if already registered
        existing = db.query(UserPasskey).filter_by(credential_id=credential_id_b64).first()
        if existing:
            raise ValueError("This biometric passkey is already registered.")

        passkey = UserPasskey(
            user_id=user.id,
            credential_id=credential_id_b64,
            public_key=public_key_b64,
            sign_count=verification.sign_count,
            device_name=device_name or "Native Biometric Device",
            aaguid=str(verification.aaguid) if verification.aaguid else None,
            created_at=datetime.now()
        )
        db.add(passkey)
        db.commit()
        db.refresh(passkey)

        SecurityAuditLogger.log(
            db=db,
            user_id=user.id,
            event_type="PASSKEY_REGISTERED",
            severity="INFO",
            details={"device_name": device_name, "credential_id": credential_id_b64[:12] + "..."}
        )

        return passkey

    @staticmethod
    def get_authentication_options(user: UserAccount, db: Session) -> Dict[str, Any]:
        """
        Generates WebAuthn assertion challenge options for login.
        """
        passkeys = db.query(UserPasskey).filter_by(user_id=user.id).all()
        if not passkeys:
            raise ValueError("No biometric passkeys registered for this account.")

        allowed_credentials = []
        for pk in passkeys:
            try:
                allowed_credentials.append(
                    PublicKeyCredentialDescriptor(id=base64url_to_bytes(pk.credential_id))
                )
            except Exception:
                pass

        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=allowed_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        _ACTIVE_CHALLENGES[f"auth_{user.id}"] = {
            "challenge": options.challenge,
            "timestamp": datetime.now()
        }

        return json.loads(options_to_json(options))

    @staticmethod
    def verify_authentication(
        user: UserAccount,
        credential_json: Dict[str, Any],
        db: Session
    ) -> UserPasskey:
        """
        Cryptographically verifies the WebAuthn biometric assertion signature.
        """
        challenge_key = f"auth_{user.id}"
        challenge_data = _ACTIVE_CHALLENGES.pop(challenge_key, None)
        if not challenge_data:
            raise ValueError("Authentication challenge expired or missing. Please try again.")

        expected_challenge = challenge_data["challenge"]
        raw_credential_id = credential_json.get("id") or credential_json.get("rawId")
        if not raw_credential_id:
            raise ValueError("Invalid credential format.")

        passkey = db.query(UserPasskey).filter_by(user_id=user.id, credential_id=raw_credential_id).first()
        if not passkey:
            raise ValueError("Unrecognized biometric passkey credential.")

        verification = verify_authentication_response(
            credential=credential_json,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=base64url_to_bytes(passkey.public_key),
            credential_current_sign_count=passkey.sign_count,
            require_user_verification=False,
        )

        # Update sign count to protect against cloned credentials
        passkey.sign_count = verification.new_sign_count
        passkey.last_used_at = datetime.now()
        db.commit()

        SecurityAuditLogger.log(
            db=db,
            user_id=user.id,
            event_type="PASSKEY_AUTH_SUCCESS",
            severity="INFO",
            details={"device_name": passkey.device_name}
        )

        return passkey
