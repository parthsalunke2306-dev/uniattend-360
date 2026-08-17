"""
UniAttend Analytics - Master CLI & Application Runner.
Provides a unified interface to initialize data, run ELT pipelines,
train ML models, generate automated PDF/Excel reports, and launch the web portal.
"""

import os
import sys
import argparse
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db_manager import init_db, get_db_session
from data.data_generator import run_full_seed
from pipeline.etl_pipeline import AttendanceETLPipeline
from ml_engine.risk_predictor import AttendanceRiskModel
from ml_engine.proxy_detector import ProxyAnomalyDetector
from reporting.automated_job import AutomatedReportingScheduler


def parse_args():
    parser = argparse.ArgumentParser(description="UniAttend Analytics Platform CLI")
    parser.add_argument("--seed", action="store_true", help="Initialize DB and seed multi-tenant synthetic data")
    parser.add_argument("--etl", action="store_true", help="Execute Bronze -> Silver -> Gold ELT pipeline")
    parser.add_argument("--train-ml", action="store_true", help="Train Random Forest attendance risk forecaster")
    parser.add_argument("--audit-proxy", action="store_true", help="Run proxy and scan anomaly detection audit")
    parser.add_argument("--reports", action="store_true", help="Generate all Excel and PDF reports")
    parser.add_argument("--app", action="store_true", help="Launch interactive Streamlit web dashboard")
    parser.add_argument("--all", action="store_true", help="Run entire end-to-end workflow (Seed -> ETL -> ML -> Reports -> Launch App)")
    return parser.parse_args()


def run_pipeline():
    print("\n[STEP 2] Running ELT Pipeline (Bronze -> Silver -> Gold)...")
    pipeline = AttendanceETLPipeline()
    return pipeline.run_pipeline()


def train_ml():
    print("\n[STEP 3] Training ML Predictive Defaulter Forecaster...")
    ml = AttendanceRiskModel()
    with get_db_session() as session:
        return ml.train(session)


def audit_proxy():
    print("\n[STEP 4] Auditing Proxy & Impossible Travel Anomalies...")
    with get_db_session() as session:
        detector = ProxyAnomalyDetector(session)
        audit_res = detector.run_full_anomaly_audit()
        print(f"  • Total Anomalies Detected: {audit_res['total_proxy_events_detected']}")
        print(f"  • Impossible Travel Swipes: {len(audit_res['impossible_travel_events'])}")
        print(f"  • Device Dumping Bursts: {len(audit_res['device_burst_events'])}")
        return audit_res


def generate_reports():
    print("\n[STEP 5] Generating Automated Institutional Reports (Excel & PDF)...")
    scheduler = AutomatedReportingScheduler()
    return scheduler.run_nightly_batch_job()


def launch_app():
    print("\n[STEP 6] Launching UniAttend 360 Interactive Portal on Streamlit...")
    app_path = os.path.join(PROJECT_ROOT, "app", "streamlit_app.py")
    python_exe = sys.executable
    streamlit_cmd = [python_exe, "-m", "streamlit", "run", app_path, "--server.headless", "true"]
    print(f"Executing: {' '.join(streamlit_cmd)}")
    subprocess.run(streamlit_cmd)


def main():
    args = parse_args()

    # Default to --all if no specific arguments provided
    if not any(vars(args).values()):
        args.all = True

    if args.all or args.seed:
        print("\n[STEP 1] Seeding Academic Hierarchy & Simulating Raw Attendance Streams...")
        run_full_seed()

    if args.all or args.etl:
        run_pipeline()

    if args.all or args.train_ml:
        train_ml()

    if args.all or args.audit_proxy:
        audit_proxy()

    if args.all or args.reports:
        generate_reports()

    if args.all or args.app:
        launch_app()


if __name__ == "__main__":
    main()
