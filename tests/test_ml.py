"""
Unit & Integration Tests for ML Feature Building, Risk Forecasting, and Proxy Detection.
"""

import pytest
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db_manager import get_db_session, init_db
from data.data_generator import seed_hierarchy_and_academics, generate_raw_attendance_stream
from pipeline.etl_pipeline import AttendanceETLPipeline
from ml_engine.feature_builder import AttendanceFeatureBuilder
from ml_engine.risk_predictor import AttendanceRiskModel
from ml_engine.proxy_detector import ProxyAnomalyDetector


@pytest.fixture(scope="module")
def prepared_db():
    init_db()
    with get_db_session() as session:
        seed_hierarchy_and_academics(session)
        generate_raw_attendance_stream(session, weeks=6)
    pipeline = AttendanceETLPipeline()
    pipeline.run_pipeline()
    yield


def test_feature_builder(prepared_db):
    with get_db_session() as session:
        builder = AttendanceFeatureBuilder(session)
        features_df = builder.build_all_features()
        assert not features_df.empty
        assert "current_attendance_pct" in features_df.columns
        assert "momentum_slope" in features_df.columns
        assert "friday_absence_rate" in features_df.columns


def test_ml_risk_model_training_and_prediction(prepared_db):
    model = AttendanceRiskModel()
    with get_db_session() as session:
        train_res = model.train(session)
        assert train_res["status"] == "trained"
        assert train_res["accuracy"] > 0.60

        # Test single prediction
        sample_feature = {
            "current_attendance_pct": 62.0,
            "early_attendance_pct": 78.0,
            "momentum_slope": -16.0,
            "friday_absence_rate": 0.55,
            "morning_absence_rate": 0.40,
            "late_ratio": 0.30,
            "max_absent_streak": 4,
            "course_credits": 4
        }
        pred = model.predict_risk(sample_feature)
        assert pred["risk_tier"] in ["CRITICAL", "HIGH"]
        assert pred["defaulter_probability"] > 0.5
        assert len(pred["key_risk_factors"]) > 0


def test_proxy_detector(prepared_db):
    with get_db_session() as session:
        detector = ProxyAnomalyDetector(session)
        audit_res = detector.run_full_anomaly_audit()
        assert "total_proxy_events_detected" in audit_res
        assert "impossible_travel_events" in audit_res
