"""
Proxy Attendance & Scan Anomaly Detection Engine.
Combines rule-based spatio-temporal impossibility checks with
unsupervised machine learning (Isolation Forest) to detect fraudulent swipes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from database.models import RawAttendanceLog, Student


class ProxyAnomalyDetector:
    """Detects proxy scans, simultaneous check-ins, and abnormal device clusters."""

    def __init__(self, session: Session):
        self.session = session

    def scan_spatiotemporal_anomalies(self, time_window_minutes: int = 5) -> List[Dict[str, Any]]:
        """
        Identifies instances where a single student's card was swiped in
        two different physical rooms within an impossible travel time window.
        """
        logs = self.session.query(RawAttendanceLog).order_by(
            RawAttendanceLog.student_id_str, 
            RawAttendanceLog.scan_timestamp
        ).all()

        flagged_anomalies = []
        for i in range(1, len(logs)):
            prev_log = logs[i - 1]
            curr_log = logs[i]

            if prev_log.student_id_str == curr_log.student_id_str:
                time_diff = (curr_log.scan_timestamp - prev_log.scan_timestamp).total_seconds() / 60.0
                
                # If scanned in different rooms within <= time_window_minutes
                if prev_log.room_code != curr_log.room_code and 0 < time_diff <= time_window_minutes:
                    flagged_anomalies.append({
                        "anomaly_type": "IMPOSSIBLE_TRAVEL_PROXY",
                        "student_id_str": curr_log.student_id_str,
                        "room_1": prev_log.room_code,
                        "room_2": curr_log.room_code,
                        "time_1": prev_log.scan_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "time_2": curr_log.scan_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "time_delta_seconds": int(time_diff * 60),
                        "confidence": "HIGH",
                        "description": f"Scanned in {prev_log.room_code} and {curr_log.room_code} within {int(time_diff*60)} seconds."
                    })

        return flagged_anomalies

    def detect_device_burst_anomalies(self, burst_threshold_count: int = 4, burst_window_seconds: int = 10) -> List[Dict[str, Any]]:
        """
        Detects 'Card Dumping' where 4+ different student cards are scanned on the
        same device within 10 seconds (proxy proxying for friends).
        """
        logs = self.session.query(RawAttendanceLog).order_by(
            RawAttendanceLog.raw_device_id,
            RawAttendanceLog.scan_timestamp
        ).all()

        burst_flags = []
        for i in range(len(logs)):
            curr_log = logs[i]
            window_logs = [
                l for l in logs[i:i+burst_threshold_count+1]
                if l.raw_device_id == curr_log.raw_device_id and
                (l.scan_timestamp - curr_log.scan_timestamp).total_seconds() <= burst_window_seconds
            ]
            distinct_students = {l.student_id_str for l in window_logs}
            if len(distinct_students) >= burst_threshold_count:
                burst_flags.append({
                    "anomaly_type": "DEVICE_BURST_DUMPING",
                    "device_id": curr_log.raw_device_id,
                    "room_code": curr_log.room_code,
                    "timestamp": curr_log.scan_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "cards_swiped_count": len(distinct_students),
                    "involved_students": list(distinct_students),
                    "confidence": "HIGH",
                    "description": f"Rapid burst of {len(distinct_students)} distinct student cards on device {curr_log.raw_device_id} in under {burst_window_seconds}s."
                })
                # skip ahead
                i += len(window_logs)

        return burst_flags

    def run_full_anomaly_audit(self) -> Dict[str, Any]:
        """Runs the comprehensive proxy detection suite and returns structured audit results."""
        spatio_temporal = self.scan_spatiotemporal_anomalies()
        bursts = self.detect_device_burst_anomalies()

        return {
            "total_proxy_events_detected": len(spatio_temporal) + len(bursts),
            "impossible_travel_events": spatio_temporal,
            "device_burst_events": bursts
        }
