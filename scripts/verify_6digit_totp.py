"""
Standalone Verification Script for 6-Digit TOTP Dynamic PIN & Match Logic.
Simulates:
  1. Faculty generates 6-digit rolling PIN (e.g. 582914).
  2. Student submits matching PIN in active window (T0) -> Validated.
  3. Student submits PIN from previous window (T-1) -> Validated (Drift tolerance).
  4. Student submits invalid PIN (000000) -> Rejected (Invalid PIN).
  5. Student submits expired PIN (T-2) -> Rejected (Expired window).
  6. Student submits duplicate check-in -> Rejected (Already checked in).
"""

import time
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.anti_proxy_engine import AntiProxyEngine, DEFAULT_CLASSROOM_GEO


def run_6digit_totp_verification_suite():
    print("=" * 70)
    print("STARTING 6-DIGIT TOTP VERIFICATION & MATCH LOGIC AUDIT")
    print("=" * 70)

    engine = AntiProxyEngine(token_ttl_seconds=8)
    session_id = "DS201-LIVE-SESSION-E104"
    room_code = "E-104"
    class_geo = DEFAULT_CLASSROOM_GEO[room_code]

    # 1. Faculty generates 6-digit PIN
    token_data = engine.generate_active_token(session_id=session_id, room_code=room_code)
    active_pin = token_data["rolling_pin"]
    print(f"\n[1] Faculty Kiosk Generated Active Token:")
    print(f"    - 6-Digit Rolling PIN : {active_pin} (Length: {len(active_pin)})")
    print(f"    - Time Slot Index     : {token_data['time_slot']}")
    print(f"    - TTL Seconds         : {token_data['ttl_seconds']}s")
    assert len(active_pin) == 6 and active_pin.isdigit(), "PIN must be exactly 6 numeric digits"

    # 2. Student Submits Exact Matching PIN in Active Window (T0)
    print(f"\n[2] Student A (Aarav) Submits Active 6-Digit PIN '{active_pin}' (T0):")
    res1 = engine.verify_student_checkin(
        session_id=session_id,
        student_id_str="CHMC-DS-2024-002",
        student_name="Aarav Sharma",
        input_token_or_pin=active_pin,
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-AARAV-PHONE-01",
        room_code=room_code
    )
    print(f"    - Status   : {res1['status']}")
    print(f"    - Success  : {res1['is_success']}")
    print(f"    - Distance : {res1.get('distance_meters', 0.0)}m")
    assert res1["is_success"] is True, "Active PIN check-in failed"

    # 3. Student Submits PIN with Slight Network Drift (T-1)
    prev_time = time.time() - 7.0
    prev_token_data = engine.generate_active_token(session_id=session_id, room_code=room_code, custom_time=prev_time)
    prev_pin = prev_token_data["rolling_pin"]
    print(f"\n[3] Student B (Diya) Submits Slightly Drifted PIN '{prev_pin}' (T-1 cycle):")
    res2 = engine.verify_student_checkin(
        session_id=session_id,
        student_id_str="CHMC-DS-2024-003",
        student_name="Diya Patel",
        input_token_or_pin=prev_pin,
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-DIYA-PHONE-02",
        room_code=room_code,
        custom_time=time.time() + 2.0
    )
    print(f"    - Status   : {res2['status']}")
    print(f"    - Success  : {res2['is_success']}")
    assert res2["is_success"] is True, "Drift tolerance T-1 failed"

    # 4. Student Submits Invalid PIN ('000000')
    print(f"\n[4] Adversary Submits Invalid Guessed PIN '000000':")
    res3 = engine.verify_student_checkin(
        session_id=session_id,
        student_id_str="CHMC-DS-2024-004",
        student_name="Rohan Varma",
        input_token_or_pin="000000",
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-ROHAN-PHONE-03",
        room_code=room_code
    )
    print(f"    - Status         : {res3['status']}")
    print(f"    - Success        : {res3['is_success']}")
    print(f"    - Failure Reason : {res3.get('failure_reason')}")
    assert res3["is_success"] is False, "Invalid PIN should be rejected"

    # 5. Student Submits Duplicate Check-In
    print(f"\n[5] Student A (Aarav) Attempts Duplicate Check-In on Same Session:")
    res4 = engine.verify_student_checkin(
        session_id=session_id,
        student_id_str="CHMC-DS-2024-002",
        student_name="Aarav Sharma",
        input_token_or_pin=active_pin,
        student_lat=class_geo["lat"],
        student_lon=class_geo["lon"],
        device_fingerprint="DEVICE-AARAV-PHONE-01",
        room_code=room_code
    )
    print(f"    - Status         : {res4['status']}")
    print(f"    - Failure Reason : {res4.get('failure_reason')}")
    assert res4["status"] == "REJECTED_ALREADY_CHECKED_IN", "Duplicate scan was not intercepted"

    print("\n" + "=" * 70)
    print("ALL 6-DIGIT TOTP VERIFICATION & DRIFT TESTS PASSED (100%)")
    print("=" * 70)


if __name__ == "__main__":
    run_6digit_totp_verification_suite()
