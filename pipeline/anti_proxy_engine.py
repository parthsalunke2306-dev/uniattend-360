"""
Smart Classroom Anti-Proxy Engine for UniAttend Analytics.
Implements Tri-Factor Anti-Proxy Verification:
  1. Micro-Rotating Cryptographic Dynamic QR Tokens (8s TTL with TOTP / HMAC-SHA256)
  2. Mobile High-Precision GPS Geofencing (50-meter classroom radius)
  3. Single-Device Hardware Fingerprint Binding (1 Phone = 1 Student Lock)
  4. Real-time Anomaly & Proxy Attempt Interception
"""

import hmac
import hashlib
import time
import math
import io
import base64
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, Tuple, Optional, List
import qrcode
from PIL import Image

# Default Secret Key for HMAC Token Generation
SECRET_SALT = "UniAttend-AntiProxy-Salt-2026-SuperSecure"

# Smt. C.H.M. College (Ulhasnagar) Campus Classroom GPS Coordinates (Default: 10.0 meters)
DEFAULT_CLASSROOM_GEO = {
    "E-104": {"name": "Extension Building Room 104 (Theory)", "lat": 19.22170, "lon": 73.16460, "radius_m": 10.0},
    "M-113": {"name": "Data Science Lab (Main Building 113)", "lat": 19.22150, "lon": 73.16440, "radius_m": 10.0},
    "M-103": {"name": "Main Building Room 103 (FOR Practical)", "lat": 19.22140, "lon": 73.16430, "radius_m": 10.0},
    "DS-LAB-1": {"name": "Data Science Lab (Main Building 113)", "lat": 19.22150, "lon": 73.16440, "radius_m": 10.0},
    "LH-201": {"name": "Extension Building Room 104 (E-104)", "lat": 19.22170, "lon": 73.16460, "radius_m": 10.0},
    "LH-202": {"name": "Extension Building Room 104 (E-104)", "lat": 19.22170, "lon": 73.16460, "radius_m": 10.0},
    "AUD-CHM": {"name": "Smt. C.H.M. College Auditorium", "lat": 19.22130, "lon": 73.16420, "radius_m": 40.0},
    "LH-101": {"name": "Lecture Hall 101", "lat": 28.54502, "lon": 77.19265, "radius_m": 10.0},
    "LH-102": {"name": "Lecture Hall 102", "lat": 28.54515, "lon": 77.19280, "radius_m": 10.0},
    "CS-LAB-A": {"name": "Computer Science Lab A", "lat": 28.54530, "lon": 77.19295, "radius_m": 10.0},
}


class AntiProxyEngine:
    """Core cryptographic and spatial engine for dynamic device-centric proxy-proof classroom attendance."""

    def __init__(self, token_ttl_seconds: int = 8, secret_key: str = SECRET_SALT):
        self.token_ttl_seconds = token_ttl_seconds
        self.secret_key = secret_key
        # Tracks {session_id: {device_fingerprint: student_id_str}}
        self.session_device_registry: Dict[str, Dict[str, str]] = {}
        # Tracks {session_id: {student_id_str: checkin_record}}
        self.session_attendance_registry: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Tracks persistent 1-Device-Per-Student hardware locks: {student_id_str: {"device_uuid": str, "device_name": str, "enrolled_at": str, "last_used_at": str}}
        self.student_hardware_locks: Dict[str, Dict[str, Any]] = {}
        # Tracks dynamic faculty device coordinates: {session_id: {"lat": float, "lon": float, "accuracy_m": float, "radius_m": float, "anchor_source": str, "updated_at": str}}
        self.session_faculty_anchors: Dict[str, Dict[str, Any]] = {}
        # Real-time incident logs of intercepted proxy attempts
        self.proxy_attempt_logs: List[Dict[str, Any]] = []
        self._incident_counter: int = 0

    # ----------------------------------------------------
    # 1. DYNAMIC FACULTY GEOFENCE ANCHOR MANAGEMENT
    # ----------------------------------------------------

    def set_faculty_anchor(
        self,
        session_id: str,
        lat: float,
        lon: float,
        accuracy_m: float = 3.0,
        radius_m: float = 10.0,
        anchor_source: str = "DEVICE_GPS"
    ) -> Dict[str, Any]:
        """
        Dynamically sets or updates the center of the geofence using the faculty device's active GPS coordinates.
        """
        anchor = {
            "session_id": session_id,
            "lat": round(float(lat), 6),
            "lon": round(float(lon), 6),
            "accuracy_m": round(float(accuracy_m), 1),
            "radius_m": round(float(radius_m), 1),
            "anchor_source": anchor_source,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.session_faculty_anchors[session_id] = anchor
        return anchor

    def get_faculty_anchor(self, session_id: str, fallback_room_code: str = "E-104") -> Dict[str, Any]:
        """
        Retrieves the active faculty anchor for the session.
        If no dynamic anchor has been registered yet, falls back to the classroom's preset coordinates.
        """
        if session_id in self.session_faculty_anchors:
            return self.session_faculty_anchors[session_id]
        
        # Fallback to classroom preset
        room_preset = DEFAULT_CLASSROOM_GEO.get(fallback_room_code, DEFAULT_CLASSROOM_GEO["E-104"])
        return {
            "session_id": session_id,
            "lat": room_preset["lat"],
            "lon": room_preset["lon"],
            "accuracy_m": 2.5,
            "radius_m": room_preset.get("radius_m", 10.0),
            "anchor_source": "ROOM_PRESET",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # ----------------------------------------------------
    # 2. DYNAMIC ROTATING QR & TOKEN GENERATION
    # ----------------------------------------------------

    def generate_active_token(self, session_id: str, room_code: str, custom_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Generates a time-bound cryptographic token and 6-digit PIN for the current window.
        Refreshes every `token_ttl_seconds` (e.g. 8 seconds).
        """
        now = custom_time if custom_time is not None else time.time()
        time_slot = int(now // self.token_ttl_seconds)
        time_remaining = self.token_ttl_seconds - (now % self.token_ttl_seconds)

        # Generate HMAC-SHA256 signature
        message = f"{session_id}:{room_code}:{time_slot}".encode("utf-8")
        signature = hmac.new(self.secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()

        # 6-Digit Rolling PIN from numeric slice of hash (RFC 6238 TOTP style % 1,000,000)
        pin_seed = int(signature[:8], 16) % 1000000
        rolling_pin = f"{pin_seed:06d}"
        
        # Token payload to embed in QR
        token_payload = {
            "s_id": session_id,
            "room": room_code,
            "slot": time_slot,
            "sig": signature[:16],
            "pin": rolling_pin
        }
        token_str = base64.urlsafe_b64encode(json.dumps(token_payload).encode()).decode()

        return {
            "token": token_str,
            "raw_payload": token_payload,
            "rolling_pin": rolling_pin,
            "time_slot": time_slot,
            "time_remaining_seconds": round(time_remaining, 1),
            "ttl_seconds": self.token_ttl_seconds,
            "timestamp": datetime.fromtimestamp(now).strftime("%H:%M:%S")
        }

    def generate_qr_image_base64(self, token_data: Dict[str, Any]) -> str:
        """Generates a Base64-encoded PNG QR image from the token payload."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2
        )
        qr.add_data(token_data["token"])
        qr.make(fit=True)

        img = qr.make_image(fill_color="#1E3A8A", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    # ----------------------------------------------------
    # 3. HAVERSINE GPS DISTANCE CALCULATOR
    # ----------------------------------------------------

    @staticmethod
    def calculate_haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates great-circle distance between two GPS coordinates on Earth in meters.
        """
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance = R * c
        return round(distance, 2)

    # ----------------------------------------------------
    # 4. PROXY INCIDENT LOGGING & NOTIFICATIONS
    # ----------------------------------------------------

    def log_proxy_attempt(
        self,
        session_id: str,
        student_id_str: str,
        student_name: str,
        attack_type: str,
        student_lat: float,
        student_lon: float,
        faculty_anchor_lat: float,
        faculty_anchor_lon: float,
        distance_meters: float,
        max_allowed_radius_m: float,
        device_fingerprint: str,
        failure_reason: str
    ) -> Dict[str, Any]:
        """Records an intercepted proxy attempt in memory and returns the incident descriptor."""
        self._incident_counter += 1
        incident = {
            "id": f"INC-{self._incident_counter:04d}",
            "session_id": session_id,
            "student_id_str": student_id_str,
            "student_name": student_name,
            "attack_type": attack_type,
            "student_lat": round(float(student_lat), 6) if student_lat else None,
            "student_lon": round(float(student_lon), 6) if student_lon else None,
            "faculty_anchor_lat": round(float(faculty_anchor_lat), 6) if faculty_anchor_lat else None,
            "faculty_anchor_lon": round(float(faculty_anchor_lon), 6) if faculty_anchor_lon else None,
            "distance_meters": round(float(distance_meters), 2) if distance_meters is not None else None,
            "max_allowed_radius_m": round(float(max_allowed_radius_m), 1),
            "device_fingerprint": (device_fingerprint[:8] + "...") if device_fingerprint else "UNKNOWN",
            "failure_reason": failure_reason,
            "is_acknowledged": False,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.proxy_attempt_logs.insert(0, incident)
        return incident

    def get_proxy_attempts(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves flagged proxy attempts, optionally filtered by lecture session ID."""
        if session_id:
            return [log for log in self.proxy_attempt_logs if log["session_id"] == session_id]
        return self.proxy_attempt_logs

    def acknowledge_proxy_attempt(self, attempt_id: str) -> bool:
        """Marks a proxy attempt as acknowledged by the instructor."""
        for log in self.proxy_attempt_logs:
            if log["id"] == attempt_id:
                log["is_acknowledged"] = True
                return True
        return False

    def clear_proxy_attempts(self, session_id: Optional[str] = None) -> int:
        """Clears proxy attempts for a session or globally."""
        if session_id:
            before_len = len(self.proxy_attempt_logs)
            self.proxy_attempt_logs = [log for log in self.proxy_attempt_logs if log["session_id"] != session_id]
            return before_len - len(self.proxy_attempt_logs)
        else:
            cleared = len(self.proxy_attempt_logs)
            self.proxy_attempt_logs = []
            return cleared

    # ----------------------------------------------------
    # 5. TRI-FACTOR ANTI-PROXY VERIFICATION ENGINE
    # ----------------------------------------------------

    def verify_student_checkin(
        self,
        session_id: str,
        student_id_str: str,
        student_name: str,
        input_token_or_pin: str,
        student_lat: float,
        student_lon: float,
        device_fingerprint: str,
        room_code: str = "LH-101",
        custom_time: Optional[float] = None,
        custom_radius_m: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validates student check-in relative to the DYNAMIC FACULTY DEVICE GEOFENCE:
          1. Cryptographic Token / PIN freshness (within TTL window)
          2. Dynamic Haversine distance check to faculty device anchor (<= radius_m)
          3. Single-Device Hardware Binding (1 phone = 1 student lock)
          4. Duplicate check (preventing double scans)
        """
        now = custom_time if custom_time is not None else time.time()
        current_slot = int(now // self.token_ttl_seconds)

        # Retrieve dynamic faculty device anchor
        anchor = self.get_faculty_anchor(session_id, fallback_room_code=room_code)
        faculty_lat = anchor["lat"]
        faculty_lon = anchor["lon"]
        max_radius = custom_radius_m if custom_radius_m is not None else anchor.get("radius_m", 10.0)

        # ------------------------------------------------
        # SHIELD 1: TOKEN / PIN FRESHNESS CHECK
        # ------------------------------------------------
        token_valid = False
        token_failure_reason = None
        
        # Check current slot and immediately adjacent slots (-1, -2 slots for network lag buffer)
        valid_slots = [current_slot, current_slot - 1, current_slot - 2]

        # Try decoding as Base64 QR Token
        try:
            decoded_json = json.loads(base64.urlsafe_b64decode(input_token_or_pin.encode()).decode())
            token_slot = decoded_json.get("slot")
            token_room = decoded_json.get("room")
            token_sid = decoded_json.get("s_id")
            
            if token_sid == session_id and token_room == room_code and token_slot in valid_slots:
                # Re-verify HMAC signature
                expected_msg = f"{session_id}:{room_code}:{token_slot}".encode("utf-8")
                expected_sig = hmac.new(self.secret_key.encode("utf-8"), expected_msg, hashlib.sha256).hexdigest()[:16]
                if decoded_json.get("sig") == expected_sig:
                    token_valid = True
                else:
                    token_failure_reason = "Cryptographic signature tampered or invalid."
            else:
                token_failure_reason = f"Expired QR Token. Generated for slot {token_slot}, current slot is {current_slot}."
        except Exception:
            # Try evaluating as 6-digit Rolling PIN
            cleaned_pin = input_token_or_pin.strip()
            for s in valid_slots:
                msg = f"{session_id}:{room_code}:{s}".encode("utf-8")
                sig = hmac.new(self.secret_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()
                pin = f"{int(sig[:8], 16) % 1000000:06d}"
                if cleaned_pin == pin:
                    token_valid = True
                    break
            if not token_valid:
                token_failure_reason = "Invalid or expired 6-Digit Security PIN."

        # ------------------------------------------------
        # SHIELD 2: DYNAMIC DEVICE-CENTRIC GEOFENCE CHECK
        # ------------------------------------------------
        distance_meters = self.calculate_haversine_distance_meters(student_lat, student_lon, faculty_lat, faculty_lon)
        geo_valid = distance_meters <= max_radius
        geo_failure_reason = None if geo_valid else f"Outside Faculty Perimeter: {distance_meters:.1f}m away (Max allowed: {max_radius:.1f}m from lecturer)."

        # ------------------------------------------------
        # ------------------------------------------------
        # SHIELD 3: 1-DEVICE-PER-STUDENT & ANTI-CYCLING HARDWARE LOCK
        # ------------------------------------------------
        session_devices = self.session_device_registry.setdefault(session_id, {})
        device_valid = True
        device_failure_reason = None
        device_attack_type = "DEVICE_SHARING_PROXY"

        # 3A: Student-to-Device Hardware Binding Check
        if student_id_str in self.student_hardware_locks:
            bound_device = self.student_hardware_locks[student_id_str]
            if bound_device.get("device_uuid") != device_fingerprint:
                device_valid = False
                device_attack_type = "DEVICE_MISMATCH_UNAUTHORIZED_HARDWARE"
                device_failure_reason = f"Unauthorized Handset! Student {student_id_str} is cryptographically locked to a different primary device."
            else:
                bound_device["last_used_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Automatic first-time hardware binding
            self.student_hardware_locks[student_id_str] = {
                "device_uuid": device_fingerprint,
                "device_name": "Primary Mobile Device",
                "enrolled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_used_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # 3B: Device-to-Student Anti-Cycling Multi-Account Check (1 Phone cannot mark for 2 students in same lecture)
        if device_valid and device_fingerprint in session_devices:
            registered_student = session_devices[device_fingerprint]
            if registered_student != student_id_str:
                device_valid = False
                device_attack_type = "DEVICE_SHARING_PROXY"
                device_failure_reason = f"Device Hardware Re-use Detected! This phone already marked attendance for {registered_student}."

        # ------------------------------------------------
        # SHIELD 4: DUPLICATE CHECK
        # ------------------------------------------------
        session_attendance = self.session_attendance_registry.setdefault(session_id, {})
        if student_id_str in session_attendance:
            return {
                "status": "REJECTED_ALREADY_CHECKED_IN",
                "is_success": False,
                "is_proxy_blocked": False,
                "student_id_str": student_id_str,
                "student_name": student_name,
                "distance_meters": distance_meters,
                "max_allowed_radius_m": max_radius,
                "faculty_anchor": anchor,
                "failure_reason": f"Student {student_id_str} is already marked Present in this active session.",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

        # ------------------------------------------------
        # FINAL VERIFICATION VERDICT
        # ------------------------------------------------
        is_success = token_valid and geo_valid and device_valid

        if is_success:
            # Register device and student in session
            session_devices[device_fingerprint] = student_id_str
            record = {
                "student_id_str": student_id_str,
                "student_name": student_name,
                "status": "PRESENT",
                "distance_meters": distance_meters,
                "max_allowed_radius_m": max_radius,
                "device_fingerprint": device_fingerprint[:8] + "...",
                "checkin_time": datetime.now().strftime("%H:%M:%S"),
                "verification_method": "ANTI_PROXY_DYNAMIC_GEOFENCE",
                "is_proxy": False
            }
            session_attendance[student_id_str] = record
            return {
                "status": "VERIFIED_PRESENT",
                "is_success": True,
                "is_proxy_blocked": False,
                "record": record,
                "distance_meters": distance_meters,
                "max_allowed_radius_m": max_radius,
                "faculty_anchor": anchor,
                "message": f"✅ Attendance Verified for {student_name} ({distance_meters:.1f}m from lecturer)."
            }
        else:
            # Classify exact Attack Pattern
            if not geo_valid:
                attack_type = "REMOTE_WHATSAPP_PROXY"
                primary_reason = geo_failure_reason
            elif not device_valid:
                attack_type = device_attack_type
                primary_reason = device_failure_reason
            else:
                attack_type = "EXPIRED_QR_PROXY"
                primary_reason = token_failure_reason
            
            # Automatically record incident in real-time proxy log
            incident = self.log_proxy_attempt(
                session_id=session_id,
                student_id_str=student_id_str,
                student_name=student_name,
                attack_type=attack_type,
                student_lat=student_lat,
                student_lon=student_lon,
                faculty_anchor_lat=faculty_lat,
                faculty_anchor_lon=faculty_lon,
                distance_meters=distance_meters,
                max_allowed_radius_m=max_radius,
                device_fingerprint=device_fingerprint,
                failure_reason=primary_reason
            )

            return {
                "status": "PROXY_ATTEMPT_BLOCKED",
                "is_success": False,
                "is_proxy_blocked": True,
                "attack_type": attack_type,
                "incident_id": incident["id"],
                "student_id_str": student_id_str,
                "student_name": student_name,
                "distance_meters": distance_meters,
                "max_allowed_radius_m": max_radius,
                "faculty_anchor": anchor,
                "failure_reason": primary_reason,
                "shields": {
                    "token_valid": token_valid,
                    "geo_valid": geo_valid,
                    "device_valid": device_valid
                },
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

    # ----------------------------------------------------
    # 6. HARDWARE DEVICE MANAGEMENT & EMERGENCY RESET
    # ----------------------------------------------------

    def bind_student_device(self, student_id_str: str, device_uuid: str, device_name: str = "Primary Mobile Handset") -> Dict[str, Any]:
        """Explicitly binds or re-binds a primary hardware device to a student account."""
        lock = {
            "device_uuid": device_uuid,
            "device_name": device_name,
            "enrolled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_used_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.student_hardware_locks[student_id_str] = lock
        return lock

    def get_student_device_status(self, student_id_str: str) -> Dict[str, Any]:
        """Returns the hardware lock and binding status for a student account."""
        if student_id_str in self.student_hardware_locks:
            return {
                "student_id_str": student_id_str,
                "is_locked": True,
                "device_info": self.student_hardware_locks[student_id_str]
            }
        return {
            "student_id_str": student_id_str,
            "is_locked": False,
            "device_info": None
        }

    def reset_student_device(self, student_id_str: str, authorized_by: str = "Faculty Admin") -> Dict[str, Any]:
        """
        Emergency Administrative Reset:
        Unlinks a student's prior hardware device, allowing legitimate re-enrollment of a new handset.
        """
        prior = self.student_hardware_locks.pop(student_id_str, None)
        return {
            "student_id_str": student_id_str,
            "status": "RESET_SUCCESSFUL",
            "unlinked_device": prior,
            "authorized_by": authorized_by,
            "reset_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"Successfully unlinked hardware lock for {student_id_str}. Student may now bind their new phone on next check-in."
        }


# Singleton engine instance for live application
anti_proxy_engine = AntiProxyEngine(token_ttl_seconds=8)
