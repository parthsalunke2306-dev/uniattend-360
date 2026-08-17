"""
UniAttend Analytics - Universal Interactive Web Portal with Role Categorization.
Implements 4 Institutional Profiles:
  1. 🏛️ Principal / Vice Chancellor (Campus-wide oversight, cross-department analytics, executive reports)
  2. 👔 Departmental Head (HOD) (Department health, course defaulter rosters, batch warning notices)
  3. 👨‍🏫 Teacher / Faculty (Smart Classroom Kiosk, rotating dynamic QR, live digital attendance sheet)
  4. 🎓 Student (Mobile check-in, live GPS verification, Student 360, 'What-If' simulator)
"""

import os
import sys
import time
from datetime import datetime, date
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy.orm import Session

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.models import (
    University, College, Department, Course, Faculty, Student, 
    TimetableSession, RawAttendanceLog, FactAttendance, StudentCourseSummary, UserAccount
)
from database.db_manager import get_db_session, init_db
from pipeline.etl_pipeline import AttendanceETLPipeline
from pipeline.anti_proxy_engine import anti_proxy_engine, DEFAULT_CLASSROOM_GEO
from pipeline.auth_manager import ProfileManager, ROLE_DEFINITIONS
from ml_engine.risk_predictor import AttendanceRiskModel
from ml_engine.proxy_detector import ProxyAnomalyDetector
from ml_engine.feature_builder import AttendanceFeatureBuilder
from reporting.excel_reporter import ExcelAttendanceReporter
from reporting.pdf_reporter import PDFReportGenerator
from reporting.automated_job import AutomatedReportingScheduler

# Page Config
st.set_page_config(
    page_title="UniAttend 360 | Universal Attendance Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .role-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 10px;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .pin-card {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .badge-safe {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-warning {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-danger {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# Persistent session state for proxy alerts
if "live_proxy_alerts" not in st.session_state:
    st.session_state.live_proxy_alerts = []


def get_tenant_data(session: Session):
    universities = session.query(University).all()
    departments = session.query(Department).all()
    courses = session.query(Course).all()
    students = session.query(Student).all()
    faculty = session.query(Faculty).all()
    user_accounts = session.query(UserAccount).all()
    return universities, departments, courses, students, faculty, user_accounts


def main():
    # Top Banner Header
    st.markdown("<div class='main-header'>🎓 UniAttend 360 Enterprise Platform</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Universal Multi-Role Attendance Tracking, Anti-Proxy Kiosk & Predictive Analytics</div>", unsafe_allow_html=True)

    with get_db_session() as session:
        universities, departments, courses, students, faculty, user_accounts = get_tenant_data(session)

        if not universities:
            st.warning("⚠️ Database is empty. Please initialize demo data below.")
            if st.button("🚀 Initialize Demo Universities & Attendance Streams"):
                with st.spinner("Seeding database and running initial ETL pipeline..."):
                    from data.data_generator import run_full_seed
                    run_full_seed()
                    pipeline = AttendanceETLPipeline()
                    pipeline.run_pipeline()
                    ml = AttendanceRiskModel()
                    ml.train(session)
                    st.success("🎉 Data seeded and processed successfully! Refreshing...")
                    st.rerun()
            return

        # ----------------------------------------------------
        # SIDEBAR: ROLE / PERSONA CATEGORIZATION
        # ----------------------------------------------------
        st.sidebar.image("https://img.icons8.com/fluency/96/university.png", width=60)
        st.sidebar.title("Institutional Portal")

        st.sidebar.markdown("### 👤 Select Active Profile")
        role_choice = st.sidebar.selectbox(
            "Logged In As:",
            ["🏛️ Principal / Vice Chancellor", "👔 Departmental Head (HOD)", "👨‍🏫 Teacher / Faculty", "🎓 Student"],
            index=0
        )

        role_code_map = {
            "🏛️ Principal / Vice Chancellor": "PRINCIPAL",
            "👔 Departmental Head (HOD)": "HOD",
            "👨‍🏫 Teacher / Faculty": "TEACHER",
            "🎓 Student": "STUDENT"
        }
        current_role = role_code_map[role_choice]
        role_meta = ROLE_DEFINITIONS[current_role]

        # Role-specific identity dropdown in sidebar
        active_user_context = {}
        if current_role == "PRINCIPAL":
            uni_principals = [u for u in user_accounts if u.role == "PRINCIPAL"]
            selected_user = st.sidebar.selectbox("Active Account:", uni_principals, format_func=lambda u: u.full_name)
            active_user_context = ProfileManager.get_user_context(session, selected_user.id) if selected_user else {}
            
            # University filter
            uni_options = {u.name: u.id for u in universities}
            selected_uni_name = st.sidebar.selectbox("Campus Scope:", list(uni_options.keys()))
            selected_uni_id = uni_options[selected_uni_name]
            scoped_depts = [d for d in departments if d.college.university_id == selected_uni_id]

        elif current_role == "HOD":
            hod_users = [u for u in user_accounts if u.role == "HOD"]
            selected_user = st.sidebar.selectbox("Active HOD Account:", hod_users, format_func=lambda u: f"{u.full_name} ({u.username})")
            active_user_context = ProfileManager.get_user_context(session, selected_user.id) if selected_user else {}
            
            dept_id = active_user_context.get("department_id") or departments[0].id
            scoped_depts = [d for d in departments if d.id == dept_id]

        elif current_role == "TEACHER":
            teacher_users = [u for u in user_accounts if u.role == "TEACHER"]
            selected_user = st.sidebar.selectbox("Active Faculty Account:", teacher_users, format_func=lambda u: u.full_name)
            active_user_context = ProfileManager.get_user_context(session, selected_user.id) if selected_user else {}
            
            dept_id = active_user_context.get("department_id") or departments[0].id
            scoped_depts = [d for d in departments if d.id == dept_id]

        elif current_role == "STUDENT":
            student_users = [u for u in user_accounts if u.role == "STUDENT"]
            selected_user = st.sidebar.selectbox("Active Student Account:", student_users, format_func=lambda u: f"{u.full_name} ({u.username})")
            active_user_context = ProfileManager.get_user_context(session, selected_user.id) if selected_user else {}
            
            dept_id = active_user_context.get("department_id") or departments[0].id
            scoped_depts = [d for d in departments if d.id == dept_id]

        # Active Profile Info Card in Sidebar
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Current Role Profile**")
        st.sidebar.caption(f"🏷️ **Role:** {role_meta['title']}")
        st.sidebar.caption(f"📌 **Description:** {role_meta['description']}")

        # Top Profile Banner in Main View
        st.markdown(f"""
        <div style='background-color: #F1F5F9; border-left: 5px solid {role_meta['badge_color']}; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;'>
            <span style='font-size: 1.3rem;'>{role_meta['icon']}</span> 
            <span style='font-weight: 700; font-size: 1.1rem; color: #1E293B;'>{active_user_context.get('full_name', role_meta['title'])}</span>
            <span style='background-color: {role_meta['badge_color']}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 10px; font-weight: 600;'>{current_role}</span>
            <div style='font-size: 0.85rem; color: #64748B; margin-top: 4px;'>{role_meta['description']}</div>
        </div>
        """, unsafe_allow_html=True)

        # ----------------------------------------------------
        # ROLE-BASED DASHBOARD RENDERING
        # ----------------------------------------------------

        # ====================================================
        # 1. PRINCIPAL VIEW (EXECUTIVE CAMPUS OVERVIEW)
        # ====================================================
        if current_role == "PRINCIPAL":
            st.markdown("### 🏛️ University Executive Dashboard (Principal / Vice Chancellor View)")
            
            # Aggregate across all scoped departments
            scoped_dept_ids = [d.id for d in scoped_depts]
            scoped_courses = [c for c in courses if c.department_id in scoped_dept_ids]
            scoped_course_ids = [c.id for c in scoped_courses]
            scoped_students = [s for s in students if s.department_id in scoped_dept_ids]
            
            all_summaries: List[StudentCourseSummary] = session.query(StudentCourseSummary).filter(
                StudentCourseSummary.course_id.in_(scoped_course_ids)
            ).all()

            if all_summaries:
                total_enrolled = len(scoped_students)
                total_enrollments = len(all_summaries)
                total_defaulters = len([s for s in all_summaries if s.is_defaulter])
                avg_campus_att = sum(s.attendance_pct for s in all_summaries) / total_enrollments if total_enrollments else 0.0

                # KPI Row
                pk1, pk2, pk3, pk4 = st.columns(4)
                pk1.metric("Total Campus Students", total_enrolled)
                pk2.metric("Active Academic Departments", len(scoped_depts))
                pk3.metric("University Average Attendance", f"{avg_campus_att:.1f}%", delta=f"{avg_campus_att - 75.0:.1f}% vs 75% Criteria")
                pk4.metric("Total Defaulter Cases (< 75%)", total_defaulters, delta=f"{(total_defaulters/total_enrollments*100):.1f}% Defaulter Rate", delta_color="inverse")

                st.markdown("---")

                # Cross-Department League Table
                p_c1, p_c2 = st.columns(2)

                with p_c1:
                    st.markdown("#### 🏆 Department Attendance League Table")
                    dept_perf = []
                    for d in scoped_depts:
                        d_c_ids = [c.id for c in courses if c.department_id == d.id]
                        d_sums = [s for s in all_summaries if s.course_id in d_c_ids]
                        d_avg = (sum(s.attendance_pct for s in d_sums) / len(d_sums)) if d_sums else 0.0
                        d_def = len([s for s in d_sums if s.is_defaulter])
                        dept_perf.append({
                            "Department": d.name,
                            "Dept Code": d.dept_code,
                            "Average Attendance %": round(d_avg, 1),
                            "Defaulters": d_def
                        })

                    df_dept_perf = pd.DataFrame(dept_perf).sort_values("Average Attendance %", ascending=False)
                    fig_dept = px.bar(
                        df_dept_perf, 
                        x="Dept Code", 
                        y="Average Attendance %", 
                        color="Average Attendance %",
                        color_continuous_scale="Teal",
                        text="Average Attendance %",
                        title="Department Attendance Comparison"
                    )
                    fig_dept.add_hline(y=75, line_dash="dash", line_color="red", annotation_text="75% Statutory Cutoff")
                    fig_dept.update_layout(height=340)
                    st.plotly_chart(fig_dept, use_container_width=True)

                with p_c2:
                    st.markdown("#### 🍩 Campus Student Eligibility Donut")
                    tiers = {"Safe (≥ 80%)": 0, "Warning (75-79%)": 0, "Defaulter (< 75%)": 0}
                    for s in all_summaries:
                        if s.attendance_pct >= 80:
                            tiers["Safe (≥ 80%)"] += 1
                        elif s.attendance_pct >= 75:
                            tiers["Warning (75-79%)"] += 1
                        else:
                            tiers["Defaulter (< 75%)"] += 1

                    df_tiers = pd.DataFrame(list(tiers.items()), columns=["Status", "Count"])
                    fig_pie = px.pie(
                        df_tiers, 
                        names="Status", 
                        values="Count", 
                        hole=0.45,
                        color="Status",
                        color_discrete_map={"Safe (≥ 80%)": "#10B981", "Warning (75-79%)": "#F59E0B", "Defaulter (< 75%)": "#EF4444"}
                    )
                    fig_pie.update_layout(height=340)
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.markdown("---")

                # Executive Actions
                st.markdown("#### 📑 Executive Compliance & Automated Audit Center")
                ex_col1, ex_col2 = st.columns(2)
                with ex_col1:
                    if st.button("🚀 Trigger Campus-Wide Automated Audit & Warning Notices"):
                        with st.spinner("Executing full nightly automated batch job..."):
                            scheduler = AutomatedReportingScheduler()
                            res = scheduler.run_nightly_batch_job()
                            st.success(f"🎉 University Audit Complete! Generated {res['excel_reports_generated']} Excels, {res['pdf_executive_reports_generated']} Executive PDFs, and issued {res['warning_letters_issued']} Defaulter Warning Letters!")

                with ex_col2:
                    st.caption("Principal has authority to download campus-wide board summaries.")
                    if st.button("📥 Generate All Department Master PDF Reports"):
                        pdf_rep = PDFReportGenerator()
                        paths = [pdf_rep.generate_department_executive_pdf(session, d.id) for d in scoped_depts]
                        st.success(f"Generated {len(paths)} official executive PDF digests.")

        # ====================================================
        # 2. HOD VIEW (DEPARTMENT HEAD PORTAL)
        # ====================================================
        elif current_role == "HOD":
            target_dept = scoped_depts[0]
            st.markdown(f"### 👔 Departmental Head Portal — {target_dept.name} ({target_dept.dept_code})")
            
            dept_courses_list = [c for c in courses if c.department_id == target_dept.id]
            dept_students_list = [s for s in students if s.department_id == target_dept.id]
            c_ids = [c.id for c in dept_courses_list]
            
            dept_summaries: List[StudentCourseSummary] = session.query(StudentCourseSummary).filter(
                StudentCourseSummary.course_id.in_(c_ids)
            ).all()

            if dept_summaries:
                h1, h2, h3, h4 = st.columns(4)
                d_enrolled = len(dept_students_list)
                d_defaulters = len([s for s in dept_summaries if s.is_defaulter])
                d_avg = sum(s.attendance_pct for s in dept_summaries) / len(dept_summaries) if dept_summaries else 0.0

                h1.metric("Department Students", d_enrolled)
                h2.metric("Active Department Courses", len(dept_courses_list))
                h3.metric("Department Average Attendance", f"{d_avg:.1f}%")
                h4.metric("Defaulter Cases (< 75%)", d_defaulters, delta=f"-{d_defaulters} Defaulters", delta_color="inverse")

                st.markdown("---")

                # Course Deep Dive & Defaulter Approval List
                h_tab1, h_tab2, h_tab3 = st.tabs(["📚 Course-Wise Performance", "🚨 Defaulter Action & Parent Notices", "📄 Department Reports Export"])

                with h_tab1:
                    c_data = []
                    for c in dept_courses_list:
                        c_sums = [s for s in dept_summaries if s.course_id == c.id]
                        c_avg_att = sum(s.attendance_pct for s in c_sums) / len(c_sums) if c_sums else 0
                        c_def_cnt = len([s for s in c_sums if s.is_defaulter])
                        c_data.append({
                            "Course Code": c.course_code,
                            "Course Name": c.course_name,
                            "Credits": c.credits,
                            "Enrolled": len(c_sums),
                            "Average Attendance %": f"{c_avg_att:.1f}%",
                            "Defaulters (<75%)": c_def_cnt
                        })
                    st.dataframe(pd.DataFrame(c_data), use_container_width=True, hide_index=True)

                with h_tab2:
                    st.markdown("#### ✉️ Issue Official Warning Notices & Parent Intimation")
                    defaulters_list = [s for s in dept_summaries if s.is_defaulter]
                    st_map = {s.id: s for s in dept_students_list}
                    cr_map = {c.id: c for c in dept_courses_list}

                    def_rows = []
                    for d in defaulters_list:
                        st_obj = st_map.get(d.student_id)
                        cr_obj = cr_map.get(d.course_id)
                        if st_obj and cr_obj:
                            def_rows.append({
                                "Roll Number": st_obj.student_id_str,
                                "Student Name": st_obj.full_name,
                                "Course": cr_obj.course_code,
                                "Current %": f"{d.attendance_pct:.1f}%",
                                "Recovery Needed": f"+{d.classes_needed_for_75} lectures",
                                "Risk Score": d.risk_score,
                                "Risk Tier": d.risk_category
                            })

                    if def_rows:
                        st.dataframe(pd.DataFrame(def_rows), use_container_width=True, hide_index=True)
                        if st.button("📨 Batch Issue Official Warning Notice PDFs to All Defaulters"):
                            with st.spinner("Generating official warning letter PDFs..."):
                                pdf_rep = PDFReportGenerator()
                                for d in defaulters_list:
                                    pdf_rep.generate_student_warning_letter_pdf(session, d.student_id)
                                st.success(f"🎉 Generated {len(defaulters_list)} personalized warning notice PDFs in output/letters directory!")
                    else:
                        st.success("🎉 No defaulters in this department!")

                with h_tab3:
                    st.markdown("#### 📥 Export Master Departmental Records")
                    if st.button("📊 Generate Department Master Excel & Executive PDF"):
                        excel_rep = ExcelAttendanceReporter()
                        pdf_rep = PDFReportGenerator()
                        x_path = excel_rep.generate_department_master_report(session, target_dept.id)
                        p_path = pdf_rep.generate_department_executive_pdf(session, target_dept.id)
                        st.success(f"Reports ready! Saved to `{os.path.basename(x_path)}` and `{os.path.basename(p_path)}`.")

        # ====================================================
        # 3. TEACHER VIEW (FACULTY CLASSROOM KIOSK & SESSIONS)
        # ====================================================
        elif current_role == "TEACHER":
            st.markdown(f"### 👨‍🏫 Teacher Classroom Portal — {active_user_context.get('full_name', 'Professor')}")
            
            target_dept = scoped_depts[0]
            teacher_courses = [c for c in courses if c.department_id == target_dept.id]
            dept_students_list = [s for s in students if s.department_id == target_dept.id]

            t_tab1, t_tab2 = st.tabs(["📱 Smart Classroom Projector Kiosk (Anti-Proxy)", "📋 My Course Attendance Roster"])

            with t_tab1:
                st.markdown("#### 🏛️ Classroom Projector Screen (Dynamic Rotating QR + 4-Digit Security PIN)")
                
                selected_course = st.selectbox("Select Lecture Session:", teacher_courses, format_func=lambda c: f"{c.course_code}: {c.course_name}")
                selected_room = st.selectbox("Select Classroom:", list(DEFAULT_CLASSROOM_GEO.keys()), index=0)
                room_geo = DEFAULT_CLASSROOM_GEO[selected_room]
                session_key = f"LIVE_SESS_{selected_course.id}_{selected_room}"

                token_data = anti_proxy_engine.generate_active_token(session_id=session_key, room_code=selected_room)
                qr_base64 = anti_proxy_engine.generate_qr_image_base64(token_data)

                col_qr, col_pin = st.columns([1, 2])

                with col_qr:
                    st.markdown(f"""
                    <div style='text-align: center; border: 2px solid #1E3A8A; border-radius: 12px; padding: 10px; background-color: white;'>
                        <img src="data:image/png;base64,{qr_base64}" width="220" />
                        <br/>
                        <small style='color: #64748B;'>⏳ Token rotates in: <b>{token_data['time_remaining_seconds']}s</b></small>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(token_data['time_remaining_seconds'] / token_data['ttl_seconds'])
                    if st.button("🔄 Refresh QR Token"):
                        st.rerun()

                with col_pin:
                    st.markdown(f"""
                    <div class='pin-card'>
                        <div style='font-size: 0.9rem; letter-spacing: 1px; text-transform: uppercase;'>Rolling Classroom Security PIN</div>
                        <div style='font-size: 3.2rem; font-weight: 800; letter-spacing: 6px; margin: 5px 0;'>{token_data['rolling_pin']}</div>
                        <div style='font-size: 0.85rem; opacity: 0.9;'>Classroom GPS: {room_geo['lat']:.4f}° N, {room_geo['lon']:.4f}° E • Radius: {room_geo['radius_m']}m</div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<br/>", unsafe_allow_html=True)
                    t_b1, t_b2 = st.columns(2)
                    with t_b1:
                        if st.button("⚡ Simulate 5 Fast Student Scans (Demo)"):
                            for sample_student in dept_students_list[:5]:
                                s_lat = room_geo["lat"] + np.random.uniform(-0.0001, 0.0001)
                                s_lon = room_geo["lon"] + np.random.uniform(-0.0001, 0.0001)
                                dev_id = f"DEV-{sample_student.student_id_str[:8]}"
                                anti_proxy_engine.verify_student_checkin(
                                    session_id=session_key,
                                    student_id_str=sample_student.student_id_str,
                                    student_name=sample_student.full_name,
                                    input_token_or_pin=token_data["token"],
                                    student_lat=s_lat,
                                    student_lon=s_lon,
                                    device_fingerprint=dev_id,
                                    room_code=selected_room
                                )
                            st.success("Simulated 5 in-class check-ins!")
                            st.rerun()

                    with t_b2:
                        if st.button("💾 Lock & Commit Attendance to Database"):
                            with st.spinner("Locking session and updating database..."):
                                active_records = anti_proxy_engine.session_attendance_registry.get(session_key, {})
                                if active_records:
                                    today_date = date.today()
                                    sess_obj = session.query(TimetableSession).filter_by(course_id=selected_course.id).first()
                                    sess_id = sess_obj.id if sess_obj else 1

                                    for roll_str, rec in active_records.items():
                                        st_obj = next((s for s in dept_students_list if s.student_id_str == roll_str), None)
                                        if st_obj:
                                            fact = session.query(FactAttendance).filter_by(
                                                student_id=st_obj.id,
                                                course_id=selected_course.id,
                                                session_date=today_date
                                            ).first()
                                            if not fact:
                                                fact = FactAttendance(
                                                    timetable_session_id=sess_id,
                                                    student_id=st_obj.id,
                                                    course_id=selected_course.id,
                                                    session_date=today_date,
                                                    checkin_time=datetime.now(),
                                                    status="PRESENT",
                                                    is_late=False,
                                                    confidence_score=1.0,
                                                    validation_notes="Verified via Teacher Kiosk"
                                                )
                                                session.add(fact)
                                    session.commit()
                                    pipeline = AttendanceETLPipeline()
                                    pipeline.process_silver_to_gold(session)
                                    st.success(f"🎉 Committed {len(active_records)} verified records!")
                                else:
                                    st.info("No scans recorded yet.")

                st.markdown("---")

                # Live Digital Roster
                st.markdown("#### 📋 Live Classroom Digital Attendance Sheet")
                live_attendance = anti_proxy_engine.session_attendance_registry.get(session_key, {})
                
                kiosk_roster_data = []
                for s in dept_students_list:
                    is_present = s.student_id_str in live_attendance
                    rec = live_attendance.get(s.student_id_str, {})
                    kiosk_roster_data.append({
                        "Roll Number": s.student_id_str,
                        "Student Name": s.full_name,
                        "Status": "🟢 VERIFIED PRESENT" if is_present else "⏳ AWAITING SCAN (ABSENT)",
                        "Check-In Time": rec.get("checkin_time", "—"),
                        "Distance from Lecturer": f"{rec.get('distance_meters', 0):.1f}m" if is_present else "—",
                        "Device Lock ID": rec.get("device_fingerprint", "—")
                    })

                df_kiosk = pd.DataFrame(kiosk_roster_data)
                st.dataframe(df_kiosk, use_container_width=True, hide_index=True)

            with t_tab2:
                st.markdown("#### 📚 Historical Attendance Log & Roster")
                c_pick = st.selectbox("Select Subject Roster:", teacher_courses, format_func=lambda c: f"{c.course_code}: {c.course_name}")
                c_sums = session.query(StudentCourseSummary).filter_by(course_id=c_pick.id).all()
                st_map = {s.id: s for s in dept_students_list}
                
                t_rows = []
                for cs in c_sums:
                    s_o = st_map.get(cs.student_id)
                    if s_o:
                        t_rows.append({
                            "Roll Number": s_o.student_id_str,
                            "Student Name": s_o.full_name,
                            "Held": cs.total_classes,
                            "Attended": cs.attended_classes,
                            "Attendance %": f"{cs.attendance_pct:.1f}%",
                            "Status": "🔴 DEFAULTER" if cs.is_defaulter else "🟢 ELIGIBLE",
                            "Classes Needed for 75%": f"+{cs.classes_needed_for_75}" if cs.is_defaulter else "0"
                        })
                st.dataframe(pd.DataFrame(t_rows), use_container_width=True, hide_index=True)

        # ====================================================
        # 4. STUDENT VIEW (MOBILE CHECK-IN & 360 PROFILE)
        # ====================================================
        elif current_role == "STUDENT":
            st_user_id = active_user_context.get("student_id")
            current_student = session.get(Student, st_user_id) if st_user_id else students[0]
            
            st.markdown(f"### 🎓 Student Mobile Portal — {current_student.full_name} (`{current_student.student_id_str}`)")

            s_tab1, s_tab2, s_tab3 = st.tabs(["📲 1. Mobile Camera Check-In (Anti-Proxy)", "📊 2. My Attendance 360 & Simulator", "✉️ 3. My Official Notices"])

            with s_tab1:
                st.markdown("#### 📲 Student Self Check-In Terminal")
                st.caption("Point your camera at the classroom projector screen or enter the rolling 4-digit PIN.")

                target_dept = scoped_depts[0]
                student_courses = [c for c in courses if c.department_id == target_dept.id]
                c_checkin = st.selectbox("Select Current Lecture Course:", student_courses, format_func=lambda c: f"{c.course_code}: {c.course_name}")
                room_checkin = st.selectbox("Select Active Classroom:", list(DEFAULT_CLASSROOM_GEO.keys()), index=0)
                room_geo = DEFAULT_CLASSROOM_GEO[room_checkin]
                s_key = f"LIVE_SESS_{c_checkin.id}_{room_checkin}"

                st_col1, st_col2 = st.columns(2)

                with st_col1:
                    dev_id = f"PHONE-UUID-{current_student.student_id_str[-4:]}"
                    st.text_input("Device Lock Identifier", value=dev_id, disabled=True)

                    st.markdown("**Physical GPS Location (Simulated for testing)**")
                    loc_option = st.radio(
                        "Current Location:",
                        [
                            "🟢 Physically In Classroom (Distance: ~10 meters from lecturer)",
                            "🔴 WhatsApp Forward Attack: Absent At Home (Distance: 1.8 km)",
                            "🔴 In Campus Cafeteria (Distance: 450 meters)"
                        ]
                    )

                    if "In Classroom" in loc_option:
                        u_lat = room_geo["lat"] + 0.00008
                        u_lon = room_geo["lon"] + 0.00008
                    elif "At Home" in loc_option:
                        u_lat = 28.56000
                        u_lon = 77.20000
                    else:
                        u_lat = room_geo["lat"] + 0.0035
                        u_lon = room_geo["lon"] + 0.0035

                    curr_tok = anti_proxy_engine.generate_active_token(session_id=s_key, room_code=room_checkin)
                    auto_fill = st.checkbox("Auto-fill Active Rolling PIN from Screen", value=True)
                    if auto_fill:
                        inp_code = curr_tok["rolling_pin"]
                        st.info(f"Active Rolling PIN from Screen: `{inp_code}` (Expires in {curr_tok['time_remaining_seconds']}s)")
                    else:
                        inp_code = st.text_input("Enter 4-Digit Security PIN or QR String", value="0000")

                    if st.button("🚀 Submit Live Check-In"):
                        res = anti_proxy_engine.verify_student_checkin(
                            session_id=s_key,
                            student_id_str=current_student.student_id_str,
                            student_name=current_student.full_name,
                            input_token_or_pin=inp_code,
                            student_lat=u_lat,
                            student_lon=u_lon,
                            device_fingerprint=dev_id,
                            room_code=room_checkin
                        )

                        if res["is_success"]:
                            st.success(f"### ✅ {res['message']}")
                            st.balloons()
                        else:
                            st.error(f"### 🚨 {res['failure_reason']}")
                            st.session_state.live_proxy_alerts.append({
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "student": f"{current_student.student_id_str} ({current_student.full_name})",
                                "attack_type": res.get("attack_type", "PROXY_VIOLATION"),
                                "reason": res["failure_reason"],
                                "distance": f"{res.get('distance_meters', 0):.1f}m"
                            })

                with st_col2:
                    st.markdown("#### 🛡️ Anti-Proxy Shield Security Status")
                    st.markdown(f"""
                    <div class='metric-card'>
                        <b>Classroom:</b> {room_geo['name']} ({room_checkin})<br/>
                        <b>Allowed Geofence Radius:</b> {room_geo['radius_m']} meters<br/>
                        <b>Token Refresh Interval:</b> 8 Seconds<br/>
                        <b>Device Hardware Binding:</b> Locked to {dev_id}
                    </div>
                    """, unsafe_allow_html=True)

            with s_tab2:
                st.markdown("#### 📊 Subject-Wise Attendance Breakdown & Eligibility Simulator")
                st_sums = session.query(StudentCourseSummary).filter_by(student_id=current_student.id).all()
                cr_map = {c.id: c for c in courses}

                overall_att = (sum(s.attendance_pct for s in st_sums) / len(st_sums)) if st_sums else 0.0
                st.metric("Overall Cumulative Attendance", f"{overall_att:.1f}%", delta="Eligible for Exams" if overall_att >= 75 else "Defaulter Warning", delta_color="normal" if overall_att >= 75 else "inverse")

                # Cards Row
                cols = st.columns(min(4, max(1, len(st_sums))))
                for idx, s in enumerate(st_sums):
                    cr = cr_map.get(s.course_id)
                    if not cr:
                        continue
                    with cols[idx % len(cols)]:
                        st.markdown(f"""
                        <div class='metric-card'>
                            <b>{cr.course_code}</b><br/>
                            <small>{cr.course_name}</small><br/>
                            <h3>{s.attendance_pct:.1f}%</h3>
                            Held: {s.total_classes} | Attended: {s.attended_classes}<br/>
                            Status: {'<span class="badge-danger">DEFAULTER</span>' if s.is_defaulter else '<span class="badge-safe">ELIGIBLE</span>'}
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("---")

                # Simulator
                st.markdown("#### 🧮 'What-If' Attendance Calculator")
                sim_c = st.selectbox("Select Course to Simulate:", st_sums, format_func=lambda s: f"{cr_map.get(s.course_id).course_code}: {cr_map.get(s.course_id).course_name} (Current: {s.attendance_pct:.1f}%)")
                if sim_c:
                    c_sim_obj = cr_map.get(sim_c.course_id)
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        att_n = st.slider("If I attend next N consecutive classes:", 0, 20, 4)
                        miss_m = st.slider("If I miss next M classes:", 0, 10, 0)
                    with sc2:
                        n_held = sim_c.total_classes + att_n + miss_m
                        n_att = sim_c.attended_classes + att_n
                        n_pct = (n_att / n_held * 100.0) if n_held > 0 else 0
                        st.metric(f"Projected {c_sim_obj.course_code} Attendance", f"{n_pct:.1f}%", delta=f"{n_pct - sim_c.attendance_pct:+.1f}%")
                        if n_pct >= 75.0:
                            st.success("✅ Projected to satisfy 75% exam requirement!")
                        else:
                            st.error("⚠️ Still below 75% cutoff.")

            with s_tab3:
                st.markdown("#### ✉️ Official Attendance Notices & Letters")
                has_shortage = any(s.is_defaulter for s in st_sums)
                if has_shortage:
                    st.warning("⚠️ You have an official Attendance Shortage Notice issued for one or more subjects.")
                    if st.button("📥 Download Official Warning Letter PDF"):
                        pdf_rep = PDFReportGenerator()
                        let_p = pdf_rep.generate_student_warning_letter_pdf(session, current_student.id)
                        with open(let_p, "rb") as f:
                            st.download_button("Click to Download PDF Notice", data=f, file_name=os.path.basename(let_p), mime="application/pdf")
                else:
                    st.success("🎉 You have clean attendance across all enrolled subjects. No shortage warning notices.")


if __name__ == "__main__":
    main()
