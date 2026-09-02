"""
Machine Learning Predictive Risk Forecaster for Student Attendance Defaulters.
Uses ensemble learning (Random Forest / Gradient Boosting) to forecast attendance shortage risk
and generate interpretable risk explanations.
"""

import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    RandomForestClassifier = None
from sqlalchemy.orm import Session

from database.models import Course, Student, StudentCourseSummary
from database.db_manager import get_db_session
from ml_engine.feature_builder import AttendanceFeatureBuilder

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model_artifacts")
MODEL_PATH = os.path.join(MODEL_DIR, "attendance_risk_model.joblib")

FEATURE_COLS = [
    "current_attendance_pct",
    "early_attendance_pct",
    "momentum_slope",
    "friday_absence_rate",
    "morning_absence_rate",
    "late_ratio",
    "max_absent_streak",
    "course_credits"
]


class AttendanceRiskModel:
    """Predictive ML model for early intervention and shortage forecasting."""

    def __init__(self):
        self.model: Optional[RandomForestClassifier] = None
        self.feature_importances_: Dict[str, float] = {}
        self._load_if_exists()

    def _load_if_exists(self):
        """Loads trained weights if available on disk."""
        if os.path.exists(MODEL_PATH):
            try:
                saved = joblib.load(MODEL_PATH)
                self.model = saved.get("model")
                self.feature_importances_ = saved.get("feature_importances", {})
                print(f"[ML Model] Loaded trained risk model from {MODEL_PATH}")
            except Exception as e:
                print(f"[ML Model] Could not load model: {e}")

    def train(self, session: Session) -> Dict[str, Any]:
        """Trains the Random Forest risk predictor on current semester feature data."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        builder = AttendanceFeatureBuilder(session)
        data = builder.build_all_features()

        if data.empty or len(data) < 15:
            print("[ML Model] Insufficient data to train model (need >= 15 records).")
            return {"status": "skipped", "reason": "insufficient_data"}

        X = data[FEATURE_COLS]
        y = data["is_defaulter"]

        # Train/Test split or full fit if small sample
        if len(data) >= 30 and len(y.unique()) > 1:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.25, random_state=42, stratify=y if y.value_counts().min() > 1 else None
            )
        else:
            X_train, X_test, y_train, y_test = X, X, y, y

        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_split=3,
            random_state=42,
            class_weight="balanced"
        )
        rf.fit(X_train, y_train)

        y_pred = rf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        
        # Calculate feature importances
        importances = dict(zip(FEATURE_COLS, rf.feature_importances_))
        sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

        self.model = rf
        self.feature_importances_ = sorted_importances

        # Save to disk
        joblib.dump({
            "model": self.model,
            "feature_importances": self.feature_importances_,
            "feature_cols": FEATURE_COLS
        }, MODEL_PATH)

        print(f"[ML Model] Successfully trained model. Test Accuracy: {acc:.2%}")
        return {
            "status": "trained",
            "accuracy": float(acc),
            "sample_count": len(data),
            "feature_importances": sorted_importances
        }

    def predict_risk(self, feature_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates risk prediction, forecasted end-of-term attendance %,
        and key explainability factors for a single student.
        """
        curr_pct = feature_row.get("current_attendance_pct", 75.0)
        slope = feature_row.get("momentum_slope", 0.0)

        # Baseline forecasted final % based on momentum
        forecasted_final_pct = max(0.0, min(100.0, curr_pct + (slope * 0.4)))

        if self.model is not None and hasattr(self.model, "classes_") and 1 in self.model.classes_:
            input_df = pd.DataFrame([{col: feature_row.get(col, 0.0) for col in FEATURE_COLS}])
            idx_1 = list(self.model.classes_).index(1)
            model_prob = float(self.model.predict_proba(input_df)[0][idx_1])
            # High-fidelity domain blend: If current attendance is already severely deficient (<65%), baseline risk is high
            if curr_pct < 65.0:
                defaulter_prob = max(model_prob, 0.88)
            elif curr_pct < 75.0:
                defaulter_prob = max(model_prob, 0.68)
            else:
                defaulter_prob = model_prob
        else:
            # Fallback heuristic
            if curr_pct < 65.0:
                defaulter_prob = 0.95
            elif curr_pct < 75.0:
                defaulter_prob = 0.70
            elif curr_pct < 80.0 and slope < -5:
                defaulter_prob = 0.45
            else:
                defaulter_prob = 0.05

        # Risk tier assignment
        if defaulter_prob >= 0.75 or curr_pct < 65.0:
            risk_tier = "CRITICAL"
        elif defaulter_prob >= 0.45 or curr_pct < 75.0:
            risk_tier = "HIGH"
        elif defaulter_prob >= 0.25 or (curr_pct < 80.0 and slope < 0):
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"

        # Explainability drivers
        risk_factors = []
        if curr_pct < 75.0:
            risk_factors.append(f"Current attendance ({curr_pct:.1f}%) is below institutional minimum (75%)")
        if slope < -5.0:
            risk_factors.append(f"Negative attendance momentum: dropped {abs(slope):.1f}% in recent weeks")
        if feature_row.get("friday_absence_rate", 0) > 0.40:
            risk_factors.append(f"Frequent Friday absenteeism ({feature_row.get('friday_absence_rate', 0)*100:.0f}% missed)")
        if feature_row.get("morning_absence_rate", 0) > 0.40:
            risk_factors.append(f"High morning session skip rate ({feature_row.get('morning_absence_rate', 0)*100:.0f}% missed)")
        if feature_row.get("max_absent_streak", 0) >= 3:
            risk_factors.append(f"Had a consecutive absence streak of {feature_row.get('max_absent_streak', 0)} sessions")
        if feature_row.get("late_ratio", 0) > 0.25:
            risk_factors.append(f"Frequent tardiness ({feature_row.get('late_ratio', 0)*100:.0f}% of attended classes were late)")

        if not risk_factors:
            risk_factors.append("Consistent attendance pattern with healthy buffer")

        return {
            "defaulter_probability": round(defaulter_prob, 3),
            "risk_score": round(defaulter_prob * 100.0, 1),
            "risk_tier": risk_tier,
            "forecasted_final_pct": round(forecasted_final_pct, 1),
            "key_risk_factors": risk_factors
        }
