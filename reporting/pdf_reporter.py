"""
Institutional PDF Report & Warning Letter Generator for UniAttend Analytics.
Uses ReportLab to create publication-grade executive summaries and official student warning notices.
"""

import os
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from database.models import Department, Course, Student, StudentCourseSummary, University, College

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "reports")
LETTERS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "letters")


class PDFReportGenerator:
    """Generates official executive summaries and student warning notice PDFs."""

    def __init__(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        os.makedirs(LETTERS_DIR, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        """Creates distinct typography styles for reports."""
        self.style_uni_title = ParagraphStyle(
            "UniTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1E3A8A"),
            alignment=1  # Centered
        )
        self.style_sub_title = ParagraphStyle(
            "SubTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#475569"),
            alignment=1
        )
        self.style_section_h1 = ParagraphStyle(
            "SectionH1",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=10,
            spaceAfter=6
        )
        self.style_body = ParagraphStyle(
            "Body",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#334155")
        )
        self.style_table_cell = ParagraphStyle(
            "TableCell",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1E293B")
        )
        self.style_table_header = ParagraphStyle(
            "TableHeader",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.white,
            alignment=1
        )

    def generate_department_executive_pdf(self, session: Session, department_id: int) -> str:
        """Generates an executive department attendance summary PDF."""
        dept = session.get(Department, department_id)
        if not dept:
            raise ValueError(f"Department ID {department_id} not found.")

        college = dept.college
        uni = college.university

        courses = session.query(Course).filter_by(department_id=dept.id).all()
        course_ids = [c.id for c in courses]
        summaries = session.query(StudentCourseSummary).filter(
            StudentCourseSummary.course_id.in_(course_ids)
        ).all()

        total_students = session.query(Student).filter_by(department_id=dept.id).count()
        total_enrollments = len(summaries)
        defaulters = [s for s in summaries if s.is_defaulter]
        avg_pct = (sum(s.attendance_pct for s in summaries) / total_enrollments) if total_enrollments > 0 else 0.0

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Executive_Attendance_{dept.dept_code}_{timestamp}.pdf"
        filepath = os.path.join(REPORTS_DIR, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        story = []

        # 1. Header
        story.append(Paragraph(uni.name.upper(), self.style_uni_title))
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"{college.name} • {dept.name}", self.style_sub_title))
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"Official Attendance Audit Report — Term {datetime.now().year}", self.style_sub_title))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=12))

        # 2. Executive KPIs Table
        story.append(Paragraph("1. Executive Summary & KPIs", self.style_section_h1))
        
        kpi_matrix = [
            [
                Paragraph("<b>Total Enrolled Students</b>", self.style_body), Paragraph(str(total_students), self.style_body),
                Paragraph("<b>Average Attendance</b>", self.style_body), Paragraph(f"<b>{avg_pct:.1f}%</b>", self.style_body)
            ],
            [
                Paragraph("<b>Active Courses</b>", self.style_body), Paragraph(str(len(courses)), self.style_body),
                Paragraph("<b>Total Defaulter Cases (<75%)</b>", self.style_body), Paragraph(f"<font color='#B91C1C'><b>{len(defaulters)} ({len(defaulters)/total_enrollments*100:.1f}%)</b></font>", self.style_body)
            ]
        ]
        t_kpi = Table(kpi_matrix, colWidths=[150, 110, 160, 120])
        t_kpi.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_kpi)
        story.append(Spacer(1, 14))

        # 3. Course Breakdown Table
        story.append(Paragraph("2. Course-Wise Attendance Distribution", self.style_section_h1))
        course_table_data = [[
            Paragraph("Code", self.style_table_header),
            Paragraph("Course Name", self.style_table_header),
            Paragraph("Held", self.style_table_header),
            Paragraph("Enrolled", self.style_table_header),
            Paragraph("Defaulters", self.style_table_header),
            Paragraph("Avg %", self.style_table_header),
        ]]

        for c in courses:
            c_sums = [s for s in summaries if s.course_id == c.id]
            c_def = len([s for s in c_sums if s.is_defaulter])
            c_avg = (sum(s.attendance_pct for s in c_sums) / len(c_sums)) if c_sums else 0.0
            total_cls = c_sums[0].total_classes if c_sums else 0

            course_table_data.append([
                Paragraph(c.course_code, self.style_table_cell),
                Paragraph(c.course_name, self.style_table_cell),
                Paragraph(str(total_cls), self.style_table_cell),
                Paragraph(str(len(c_sums)), self.style_table_cell),
                Paragraph(f"<font color='#B91C1C'><b>{c_def}</b></font>" if c_def > 0 else "0", self.style_table_cell),
                Paragraph(f"<b>{c_avg:.1f}%</b>", self.style_table_cell),
            ])

        t_course = Table(course_table_data, colWidths=[65, 235, 55, 60, 65, 60])
        t_course.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t_course)
        story.append(Spacer(1, 14))

        # 4. Critical Defaulter List (Top 10)
        story.append(Paragraph("3. Critical Action List (Students with Attendance < 75%)", self.style_section_h1))
        defaulter_table_data = [[
            Paragraph("Roll No", self.style_table_header),
            Paragraph("Student Name", self.style_table_header),
            Paragraph("Course", self.style_table_header),
            Paragraph("Attended/Held", self.style_table_header),
            Paragraph("Current %", self.style_table_header),
            Paragraph("Classes Needed", self.style_table_header),
        ]]

        students_map = {s.id: s for s in session.query(Student).filter_by(department_id=dept.id).all()}
        courses_map = {c.id: c for c in courses}

        sorted_defaulters = sorted(defaulters, key=lambda x: x.attendance_pct)[:12]
        for d in sorted_defaulters:
            st = students_map.get(d.student_id)
            cr = courses_map.get(d.course_id)
            if not st or not cr:
                continue

            defaulter_table_data.append([
                Paragraph(st.student_id_str, self.style_table_cell),
                Paragraph(st.full_name, self.style_table_cell),
                Paragraph(cr.course_code, self.style_table_cell),
                Paragraph(f"{d.attended_classes} / {d.total_classes}", self.style_table_cell),
                Paragraph(f"<font color='#B91C1C'><b>{d.attendance_pct:.1f}%</b></font>", self.style_table_cell),
                Paragraph(f"<b>+{d.classes_needed_for_75} consecutive</b>", self.style_table_cell),
            ])

        t_def = Table(defaulter_table_data, colWidths=[90, 160, 75, 80, 65, 70])
        t_def.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B91C1C")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF1F2")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t_def)
        story.append(Spacer(1, 25))

        # Signatures
        sig_data = [
            [Paragraph("____________________________<br/><b>Head of Department</b>", self.style_body),
             Paragraph("____________________________<br/><b>Dean of Academic Affairs</b>", self.style_body)]
        ]
        t_sig = Table(sig_data, colWidths=[270, 270])
        t_sig.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t_sig)

        doc.build(story)
        print(f"[PDF REPORTER] Generated Executive PDF at: {filepath}")
        return filepath

    def generate_student_warning_letter_pdf(self, session: Session, student_id: int) -> str:
        """
        Generates an official personalized warning letter notice for a student
        falling below the mandatory 75% attendance criteria.
        """
        student = session.get(Student, student_id)
        if not student:
            raise ValueError(f"Student ID {student_id} not found.")

        dept = student.department
        college = dept.college
        uni = college.university

        summaries = session.query(StudentCourseSummary).filter_by(student_id=student.id).all()
        courses_map = {c.id: c for c in session.query(Course).filter_by(department_id=dept.id).all()}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Warning_Notice_{student.student_id_str}_{timestamp}.pdf"
        filepath = os.path.join(LETTERS_DIR, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=45,
            leftMargin=45,
            topMargin=45,
            bottomMargin=45
        )

        story = []

        # Header
        story.append(Paragraph(uni.name.upper(), self.style_uni_title))
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"{college.name} • {dept.name}", self.style_sub_title))
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#B91C1C"), spaceAfter=14))

        # Title
        notice_style = ParagraphStyle(
            "NoticeTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#B91C1C"),
            alignment=1
        )
        story.append(Paragraph("OFFICIAL NOTICE: ATTENDANCE SHORTAGE WARNING", notice_style))
        story.append(Spacer(1, 14))

        # Student Details Block
        details_text = f"""
        <b>Date:</b> {datetime.now().strftime('%d %B %Y')}<br/>
        <b>To:</b> {student.full_name}<br/>
        <b>Enrollment / Roll No:</b> {student.student_id_str}<br/>
        <b>Department:</b> {dept.name}<br/>
        <b>Semester / Batch:</b> Semester {student.semester} (Batch {student.batch_year})<br/>
        <b>Email:</b> {student.email}
        """
        story.append(Paragraph(details_text, self.style_body))
        story.append(Spacer(1, 12))

        # Notice Statement
        statement = """
        This official communication is to notify you and your guardians that your aggregate/subject attendance
        in the current academic term has fallen below the <b>mandatory institutional minimum of 75.0%</b>.
        Under the provisions of Academic Regulation Section 4.2, students failing to maintain at least 75%
        attendance will be <b>strictly debarred</b> from appearing in the End-Semester Final Examinations.
        """
        story.append(Paragraph(statement, self.style_body))
        story.append(Spacer(1, 12))

        # Subject breakdown table
        story.append(Paragraph("<b>Subject-Wise Attendance Breakdown:</b>", self.style_section_h1))
        
        table_data = [[
            Paragraph("Course Code", self.style_table_header),
            Paragraph("Course Title", self.style_table_header),
            Paragraph("Held", self.style_table_header),
            Paragraph("Attended", self.style_table_header),
            Paragraph("Attendance %", self.style_table_header),
            Paragraph("Status", self.style_table_header),
            Paragraph("Classes Needed", self.style_table_header),
        ]]

        for s in summaries:
            cr = courses_map.get(s.course_id)
            if not cr:
                continue

            pct_color = "#B91C1C" if s.is_defaulter else "#166534"
            status_str = f"<font color='{pct_color}'><b>{'DEFAULTER' if s.is_defaulter else 'ELIGIBLE'}</b></font>"
            needed_str = f"<b>+{s.classes_needed_for_75}</b>" if s.is_defaulter else "0"

            table_data.append([
                Paragraph(cr.course_code, self.style_table_cell),
                Paragraph(cr.course_name, self.style_table_cell),
                Paragraph(str(s.total_classes), self.style_table_cell),
                Paragraph(str(s.attended_classes), self.style_table_cell),
                Paragraph(f"<font color='{pct_color}'><b>{s.attendance_pct:.1f}%</b></font>", self.style_table_cell),
                Paragraph(status_str, self.style_table_cell),
                Paragraph(needed_str, self.style_table_cell),
            ])

        t_sub = Table(table_data, colWidths=[70, 180, 45, 55, 65, 60, 65])
        t_sub.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t_sub)
        story.append(Spacer(1, 14))

        # Instructions
        action_text = """
        <b>Mandatory Action Required:</b><br/>
        1. You are directed to meet your respective Course Instructors and Faculty Advisor within <b>3 working days</b>.<br/>
        2. Ensure 100% attendance in all upcoming lectures to bridge the required shortfall.<br/>
        3. Submit any medical certificates or official leave records to the Academic Cell immediately.
        """
        story.append(Paragraph(action_text, self.style_body))
        story.append(Spacer(1, 25))

        # Signature
        sig_block = [
            [Paragraph("____________________________<br/><b>Dean / Controller of Examinations</b>", self.style_body),
             Paragraph("____________________________<br/><b>Student / Parent Acknowledgment</b>", self.style_body)]
        ]
        t_sig = Table(sig_block, colWidths=[260, 260])
        t_sig.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(t_sig)

        doc.build(story)
        print(f"[PDF REPORTER] Generated Student Warning Letter at: {filepath}")
        return filepath
