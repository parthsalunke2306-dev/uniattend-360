"""
Feature Engineering Engine for Attendance Risk & ML Modeling.
Extracts time-series signals, momentum slopes, day-of-week slump metrics,
and streak statistics from Silver FactAttendance records.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import FactAttendance, Student, Course, TimetableSession, StudentCourseSummary


class AttendanceFeatureBuilder:
    """Extracts machine learning features for attendance prediction."""

    def __init__(self, session: Session):
        self.session = session

    def build_dataset_for_course(self, course_id: int) -> pd.DataFrame:
        """Extracts tabular ML features for all students enrolled in a specific course."""
        facts: List[FactAttendance] = self.session.query(FactAttendance).filter_by(
            course_id=course_id
        ).order_by(FactAttendance.session_date.asc()).all()

        if not facts:
            return pd.DataFrame()

        # Convert to DataFrame
        records = []
        for f in facts:
            sess = f.session
            records.append({
                "student_id": f.student_id,
                "course_id": f.course_id,
                "session_date": pd.to_datetime(f.session_date),
                "day_of_week": sess.day_of_week if sess else "Monday",
                "start_hour": sess.start_time.hour if sess else 9,
                "status": f.status,
                "is_attended": 1 if f.status in ["PRESENT", "LATE"] else 0,
                "is_late": 1 if f.status == "LATE" else 0,
                "is_absent": 1 if f.status == "ABSENT" else 0
            })

        df = pd.DataFrame(records)
        return self._extract_student_features(df, course_id)

    def build_all_features(self) -> pd.DataFrame:
        """Builds dataset across all courses for global model training."""
        courses = self.session.query(Course).all()
        all_dfs = []
        for c in courses:
            c_df = self.build_dataset_for_course(c.id)
            if not c_df.empty:
                all_dfs.append(c_df)

        if not all_dfs:
            return pd.DataFrame()

        return pd.concat(all_dfs, ignore_index=True)

    def _extract_student_features(self, df: pd.DataFrame, course_id: int) -> pd.DataFrame:
        """Transforms raw event dataframe into per-student feature vectors."""
        student_groups = df.groupby("student_id")
        features_list = []

        course = self.session.get(Course, course_id)
        course_credits = course.credits if course else 3

        min_date = df["session_date"].min()
        max_date = df["session_date"].max()
        total_duration_days = (max_date - min_date).days if (max_date - min_date).days > 0 else 1
        half_date = min_date + timedelta(days=total_duration_days // 2)

        for student_id, group in student_groups:
            group = group.sort_values("session_date")
            total_sessions = len(group)
            if total_sessions == 0:
                continue

            attended_sessions = group["is_attended"].sum()
            late_sessions = group["is_late"].sum()
            absent_sessions = group["is_absent"].sum()
            current_pct = (attended_sessions / total_sessions) * 100.0

            # 1. Early-half vs Late-half momentum slope
            early_group = group[group["session_date"] <= half_date]
            late_group = group[group["session_date"] > half_date]

            early_pct = (early_group["is_attended"].sum() / len(early_group) * 100.0) if len(early_group) > 0 else current_pct
            late_pct = (late_group["is_attended"].sum() / len(late_group) * 100.0) if len(late_group) > 0 else current_pct
            attendance_momentum_slope = late_pct - early_pct

            # 2. Friday absence rate
            friday_classes = group[group["day_of_week"] == "Friday"]
            friday_absence_rate = (friday_classes["is_absent"].sum() / len(friday_classes)) if len(friday_classes) > 0 else 0.0

            # 3. Morning absence rate (start_hour <= 9)
            morning_classes = group[group["start_hour"] <= 9]
            morning_absence_rate = (morning_classes["is_absent"].sum() / len(morning_classes)) if len(morning_classes) > 0 else 0.0

            # 4. Late ratio
            late_ratio = (late_sessions / attended_sessions) if attended_sessions > 0 else 0.0

            # 5. Longest consecutive absent streak
            attendance_series = group["is_attended"].tolist()
            max_absent_streak = 0
            current_streak = 0
            for att in attendance_series:
                if att == 0:
                    current_streak += 1
                    max_absent_streak = max(max_absent_streak, current_streak)
                else:
                    current_streak = 0

            # 6. Target label for training: Is Defaulter (< 75%)
            is_defaulter_label = 1 if current_pct < 75.0 else 0

            features_list.append({
                "student_id": student_id,
                "course_id": course_id,
                "total_sessions": total_sessions,
                "attended_sessions": attended_sessions,
                "current_attendance_pct": round(current_pct, 2),
                "early_attendance_pct": round(early_pct, 2),
                "late_attendance_pct": round(late_pct, 2),
                "momentum_slope": round(attendance_momentum_slope, 2),
                "friday_absence_rate": round(friday_absence_rate, 3),
                "morning_absence_rate": round(morning_absence_rate, 3),
                "late_ratio": round(late_ratio, 3),
                "max_absent_streak": max_absent_streak,
                "course_credits": course_credits,
                "is_defaulter": is_defaulter_label
            })

        return pd.DataFrame(features_list)
