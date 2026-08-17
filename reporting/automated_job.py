"""
Automated Scheduled Batch Reporting & Dispatch Worker for UniAttend Analytics.
Simulates a daily/weekly cron job that computes attendance, generates institutional PDFs/Excels,
and issues automated warning letters to at-risk students.
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from database.models import Department, Student, StudentCourseSummary
from database.db_manager import get_db_session
from pipeline.etl_pipeline import AttendanceETLPipeline
from ml_engine.risk_predictor import AttendanceRiskModel
from reporting.excel_reporter import ExcelAttendanceReporter
from reporting.pdf_reporter import PDFReportGenerator


class AutomatedReportingScheduler:
    """Orchestrates scheduled batch reporting jobs across all departments."""

    def __init__(self):
        self.etl = AttendanceETLPipeline()
        self.ml_model = AttendanceRiskModel()
        self.excel_reporter = ExcelAttendanceReporter()
        self.pdf_reporter = PDFReportGenerator()

    def run_nightly_batch_job(self) -> Dict[str, Any]:
        """
        Executes full nightly workflow:
          1. Run ELT pipeline (Bronze -> Silver -> Gold).
          2. Train/update ML risk model.
          3. Generate department Master Excel sheets.
          4. Generate Executive Department PDFs.
          5. Generate personalized Warning Letters for all defaulter students (<75%).
        """
        print(f"\n=======================================================")
        print(f"[CRON JOB] Starting Automated Reporting Batch at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"=======================================================")

        # 1. Run ELT Pipeline
        etl_results = self.etl.run_pipeline()

        generated_excels = []
        generated_pdfs = []
        generated_warning_letters = []

        with get_db_session() as session:
            # 2. Train ML Model
            self.ml_model.train(session)

            # 3. Process each department
            departments = session.query(Department).all()

            for dept in departments:
                # Generate Excel
                excel_path = self.excel_reporter.generate_department_master_report(session, dept.id)
                generated_excels.append(excel_path)

                # Generate Executive PDF
                pdf_path = self.pdf_reporter.generate_department_executive_pdf(session, dept.id)
                generated_pdfs.append(pdf_path)

                # Find all defaulters in this department and issue warning letters
                dept_students = session.query(Student).filter_by(department_id=dept.id).all()
                for student in dept_students:
                    # Check if student is a defaulter in any course
                    has_shortage = session.query(StudentCourseSummary).filter_by(
                        student_id=student.id, is_defaulter=True
                    ).first()

                    if has_shortage:
                        letter_path = self.pdf_reporter.generate_student_warning_letter_pdf(session, student.id)
                        generated_warning_letters.append(letter_path)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "etl_metrics": etl_results,
            "total_departments_audited": len(departments),
            "excel_reports_generated": len(generated_excels),
            "pdf_executive_reports_generated": len(generated_pdfs),
            "warning_letters_issued": len(generated_warning_letters),
            "sample_excel_path": generated_excels[0] if generated_excels else None,
            "sample_pdf_path": generated_pdfs[0] if generated_pdfs else None,
            "sample_letter_path": generated_warning_letters[0] if generated_warning_letters else None,
        }

        print(f"\n=======================================================")
        print(f"[CRON JOB] Batch Run Completed Successfully!")
        print(f"  • Excel Reports: {len(generated_excels)}")
        print(f"  • Executive PDFs: {len(generated_pdfs)}")
        print(f"  • Defaulter Letters Issued: {len(generated_warning_letters)}")
        print(f"=======================================================\n")

        return summary


if __name__ == "__main__":
    scheduler = AutomatedReportingScheduler()
    res = scheduler.run_nightly_batch_job()
