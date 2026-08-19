"""
Smt. C.H.M. College - Department of Data Science Synthetic Data Generator.
Configured specifically for the Second Year (S.Y. B.Sc. Data Science) curriculum:
  - Department: Department of Data Science
  - Academic Years: First Year, Second Year, Third Year
  - Active Class: Second Year (S.Y. B.Sc. Data Science)
  - Faculty & Subject Mapping:
      1. Miss Razia Khan:
         - Data Mining (Theory)
         - Data Mining (Practical)
         - Linear Algebra
         - FOR - Foundations of Research / Operations Research (Theory)
      2. Mr. Anshul Chimnani:
         - Data Warehousing
         - FOR - Foundations of Research / Operations Research (Practical)
      3. Miss Kalyani Patil:
         - Design and Analysis of Algorithm (Theory)
         - Design and Analysis of Algorithm (Practical)
  - Students: Exactly 5 Data Science Students (Captain, Aarav, Priya, Rohan, Ananya)
"""

import os
import sys
import random
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy.orm import Session

from database.models import (
    University, College, Department, Course, Faculty, Student, 
    TimetableSession, RawAttendanceLog, UserAccount
)
from database.db_manager import get_db_session, init_db, drop_db

random.seed(42)

# Specific Configuration for Smt. C.H.M. College (Second Year Data Science)
COLLEGE_CONFIG = {
    "university_name": "University of Mumbai",
    "university_code": "MU",
    "college_name": "Smt. C.H.M. College (Ulhasnagar)",
    "campus_code": "CHMC",
    "city": "Ulhasnagar, Mumbai",
    "principal": "Dr. Manju Lalwani Pathak",
    "coordinator": "Mrs. Shiji Johnson",
    "department_name": "Department of Data Science",
    "dept_code": "CHMC-DS",
    "academic_years": ["First Year", "Second Year", "Third Year"],
    "active_class": "Second Year (S.Y. B.Sc. Data Science)",
    "faculty_members": [
        {
            "id_str": "FAC-CHMC-DS-01",
            "name": "Miss Razia Khan",
            "email": "razia.khan@chmc.edu",
            "username": "razia.khan",
            "designation": "Assistant Professor"
        },
        {
            "id_str": "FAC-CHMC-DS-02",
            "name": "Mr. Anshul Chimnani",
            "email": "anshul.chimnani@chmc.edu",
            "username": "anshul.chimnani",
            "designation": "Assistant Professor"
        },
        {
            "id_str": "FAC-CHMC-DS-03",
            "name": "Miss Kalyani Patil",
            "email": "kalyani.patil@chmc.edu",
            "username": "kalyani.patil",
            "designation": "Assistant Professor"
        }
    ],
    "sy_curriculum": [
        # Miss Razia Khan's subjects
        {
            "faculty_name": "Miss Razia Khan",
            "course_name": "Data Mining (Theory)",
            "course_code": "DS201-DM-TH",
            "type": "Theory",
            "room": "E-104",
            "days": ["Monday", "Wednesday"],
            "credits": 3,
            "semester": 3
        },
        {
            "faculty_name": "Miss Razia Khan",
            "course_name": "Data Mining (Practical)",
            "course_code": "DS201-DM-PR",
            "type": "Practical",
            "room": "M-113",
            "days": ["Friday"],
            "credits": 2,
            "semester": 3
        },
        {
            "faculty_name": "Miss Razia Khan",
            "course_name": "Linear Algebra",
            "course_code": "DS202-LA",
            "type": "Theory",
            "room": "E-104",
            "days": ["Tuesday", "Thursday"],
            "credits": 3,
            "semester": 3
        },
        {
            "faculty_name": "Miss Razia Khan",
            "course_name": "FOR - Foundations of Research (Theory)",
            "course_code": "DS203-FOR-TH",
            "type": "Theory",
            "room": "E-104",
            "days": ["Monday", "Thursday"],
            "credits": 3,
            "semester": 3
        },
        # Mr. Anshul Chimnani's subjects
        {
            "faculty_name": "Mr. Anshul Chimnani",
            "course_name": "Data Warehousing",
            "course_code": "DS204-DW",
            "type": "Theory",
            "room": "E-104",
            "days": ["Tuesday", "Thursday", "Friday"],
            "credits": 3,
            "semester": 3
        },
        {
            "faculty_name": "Mr. Anshul Chimnani",
            "course_name": "FOR - Foundations of Research (Practical)",
            "course_code": "DS203-FOR-PR",
            "type": "Practical",
            "room": "M-103",
            "days": ["Wednesday"],
            "credits": 2,
            "semester": 3
        },
        # Miss Kalyani Patil's subjects
        {
            "faculty_name": "Miss Kalyani Patil",
            "course_name": "Design and Analysis of Algorithms (Theory)",
            "course_code": "DS205-DAA-TH",
            "type": "Theory",
            "room": "E-104",
            "days": ["Monday", "Wednesday"],
            "credits": 3,
            "semester": 3
        },
        {
            "faculty_name": "Miss Kalyani Patil",
            "course_name": "Design and Analysis of Algorithms (Practical)",
            "course_code": "DS205-DAA-PR",
            "type": "Practical",
            "room": "M-113",
            "days": ["Thursday"],
            "credits": 2,
            "semester": 3
        }
    ],
    "students": [
        {"roll_no": "CHMC-DS-2024-001", "name": "Captain (Lead Data Science)", "email": "captain.ds@chmc.edu", "archetype": "exemplary"},
        {"roll_no": "CHMC-DS-2024-002", "name": "Aarav Sharma", "email": "aarav.sharma@chmc.edu", "archetype": "consistent"},
        {"roll_no": "CHMC-DS-2024-003", "name": "Priya Patel", "email": "priya.patel@chmc.edu", "archetype": "slacker"},
        {"roll_no": "CHMC-DS-2024-004", "name": "Rohan Gupta", "email": "rohan.gupta@chmc.edu", "archetype": "chronic_defaulter"},
        {"roll_no": "CHMC-DS-2024-005", "name": "Ananya Verma", "email": "ananya.verma@chmc.edu", "archetype": "consistent"}
    ]
}

TIME_SLOTS = [
    (time(9, 0), time(10, 0)),
    (time(10, 15), time(11, 15)),
    (time(11, 30), time(12, 30)),
    (time(13, 0), time(14, 0)),
    (time(14, 15), time(16, 15))  # Practical Slot (2 hrs)
]


def seed_chmc_academics(session: Session) -> Dict[str, list]:
    """Populates Smt. C.H.M. College hierarchy, Second Year curriculum, and 5 students."""
    print("[DATA GEN] Seeding Smt. C.H.M. College (Second Year Data Science Department)...")

    # 1. University
    uni = session.query(University).filter_by(code=COLLEGE_CONFIG["university_code"]).first()
    if not uni:
        uni = University(name=COLLEGE_CONFIG["university_name"], code=COLLEGE_CONFIG["university_code"])
        session.add(uni)
        session.flush()

    # 2. College
    college = session.query(College).filter_by(campus_code=COLLEGE_CONFIG["campus_code"]).first()
    if not college:
        college = College(
            university_id=uni.id,
            name=COLLEGE_CONFIG["college_name"],
            campus_code=COLLEGE_CONFIG["campus_code"],
            city=COLLEGE_CONFIG["city"]
        )
        session.add(college)
        session.flush()

    # 3. Department
    dept = session.query(Department).filter_by(dept_code=COLLEGE_CONFIG["dept_code"]).first()
    if not dept:
        dept = Department(
            college_id=college.id,
            name=COLLEGE_CONFIG["department_name"],
            dept_code=COLLEGE_CONFIG["dept_code"]
        )
        session.add(dept)
        session.flush()

    # 4. Faculty Members
    faculty_by_name = {}
    all_faculty = []
    for f_info in COLLEGE_CONFIG["faculty_members"]:
        fac = session.query(Faculty).filter_by(faculty_id_str=f_info["id_str"]).first()
        if not fac:
            fac = Faculty(
                department_id=dept.id,
                faculty_id_str=f_info["id_str"],
                full_name=f_info["name"],
                email=f_info["email"],
                designation=f_info["designation"]
            )
            session.add(fac)
            session.flush()
        faculty_by_name[f_info["name"]] = fac
        all_faculty.append(fac)

    # 5. Courses & Timetable Sessions (Second Year Curriculum)
    all_courses = []
    all_sessions = []

    for idx, c_info in enumerate(COLLEGE_CONFIG["sy_curriculum"]):
        course = session.query(Course).filter_by(course_code=c_info["course_code"]).first()
        if not course:
            course = Course(
                department_id=dept.id,
                course_name=c_info["course_name"],
                course_code=c_info["course_code"],
                credits=c_info["credits"],
                semester=c_info["semester"],
                minimum_attendance_pct=75.0
            )
            session.add(course)
            session.flush()
        all_courses.append(course)

        assigned_fac = faculty_by_name.get(c_info["faculty_name"])
        room = c_info["room"]
        slot = TIME_SLOTS[4] if c_info["type"] == "Practical" else TIME_SLOTS[idx % 4]

        for day in c_info["days"]:
            session_obj = session.query(TimetableSession).filter_by(
                course_id=course.id, day_of_week=day, start_time=slot[0]
            ).first()
            if not session_obj:
                session_obj = TimetableSession(
                    course_id=course.id,
                    faculty_id=assigned_fac.id if assigned_fac else all_faculty[0].id,
                    room_number=room,
                    day_of_week=day,
                    start_time=slot[0],
                    end_time=slot[1],
                    session_type=c_info["type"]
                )
                session.add(session_obj)
                session.flush()
            all_sessions.append(session_obj)

    # 6. Exactly 5 Students (Preserving existing student accounts)
    all_students = []
    for s_info in COLLEGE_CONFIG["students"]:
        student = session.query(Student).filter_by(student_id_str=s_info["roll_no"]).first()
        if not student:
            student = Student(
                department_id=dept.id,
                student_id_str=s_info["roll_no"],
                full_name=s_info["name"],
                email=s_info["email"],
                batch_year=2024,
                semester=3,  # Second Year (Sem 3)
                rfid_card_id=f"RFID-{s_info['roll_no'][-6:]}"
            )
            session.add(student)
            session.flush()
        all_students.append(student)

    session.commit()
    print(f"[DATA GEN] Successfully seeded Second Year Data Science: {len(all_students)} students, {len(all_courses)} course units, {len(all_faculty)} faculty.")
    return {
        "students": all_students,
        "courses": all_courses,
        "faculty": all_faculty,
        "sessions": all_sessions,
        "dept": dept,
        "college": college,
        "uni": uni
    }


def seed_chmc_user_accounts(session: Session):
    """Seeds official profiles for Principal, Coordinator, 3 Faculty, and 5 Students."""
    print("[DATA GEN] Seeding Smt. C.H.M. College User Profiles...")

    uni = session.query(University).filter_by(code=COLLEGE_CONFIG["university_code"]).first()
    dept = session.query(Department).filter_by(dept_code=COLLEGE_CONFIG["dept_code"]).first()

    from api.security import PasswordHasherService
    default_pw_hash = PasswordHasherService.hash("CHMC@2026!")

    # 1. Principal: Dr. Manju Lalwani Pathak
    p_user = session.query(UserAccount).filter_by(username="principal.chmc").first()
    if not p_user:
        p_user = UserAccount(
            username="principal.chmc",
            email="principal@chmc.edu",
            password_hash=default_pw_hash,
            full_name=f"{COLLEGE_CONFIG['principal']} (Principal, Smt. C.H.M. College)",
            role="PRINCIPAL",
            university_id=uni.id,
            avatar_icon="🏛️"
        )
        session.add(p_user)

    # 2. Course Coordinator: Mrs. Shiji Johnson
    c_user = session.query(UserAccount).filter_by(username="coordinator.ds").first()
    if not c_user:
        c_user = UserAccount(
            username="coordinator.ds",
            email="shiji.johnson@chmc.edu",
            password_hash=default_pw_hash,
            full_name=f"{COLLEGE_CONFIG['coordinator']} (Course Coordinator, Data Science)",
            role="HOD",
            university_id=uni.id,
            department_id=dept.id,
            avatar_icon="👔"
        )
        session.add(c_user)

    # 3. Faculty Accounts
    all_faculty = session.query(Faculty).all()
    for fac in all_faculty:
        uname = fac.full_name.lower().replace("miss ", "").replace("mr. ", "").replace(" ", ".")
        f_user = session.query(UserAccount).filter_by(username=uname).first()
        if not f_user:
            f_user = UserAccount(
                username=uname,
                email=fac.email,
                password_hash=default_pw_hash,
                full_name=f"{fac.full_name} (Faculty)",
                role="TEACHER",
                university_id=uni.id,
                department_id=dept.id,
                faculty_id=fac.id,
                avatar_icon="👨‍🏫"
            )
            session.add(f_user)

    # 4. 5 Student Accounts
    all_students = session.query(Student).all()
    for st in all_students:
        s_uname = st.student_id_str.lower().replace("-", ".")
        s_user = session.query(UserAccount).filter_by(username=s_uname).first()
        if not s_user:
            s_user = UserAccount(
                username=s_uname,
                email=st.email,
                password_hash=default_pw_hash,
                full_name=f"{st.full_name} ({st.student_id_str})",
                role="STUDENT",
                university_id=uni.id,
                department_id=dept.id,
                student_id=st.id,
                avatar_icon="🎓"
            )
            session.add(s_user)

    session.commit()
    print("[DATA GEN] User accounts for Smt. C.H.M. College seeded successfully with Argon2id password hashes.")


def generate_chmc_attendance_stream(session: Session, weeks: int = 8) -> int:
    """Simulates realistic attendance logs across 8 weeks for the 5 students in Smt. C.H.M. College."""
    print(f"[DATA GEN] Simulating {weeks} weeks of attendance logs for 5 Data Science students...")

    students = session.query(Student).all()
    sessions = session.query(TimetableSession).all()

    student_archetypes = {
        "CHMC-DS-2024-001": 0.95,  # Captain: Exemplary (~95%)
        "CHMC-DS-2024-002": 0.88,  # Aarav: Consistent (~88%)
        "CHMC-DS-2024-003": 0.72,  # Priya: Borderline / Warning (~72%)
        "CHMC-DS-2024-004": 0.52,  # Rohan: Chronic Defaulter (~52%)
        "CHMC-DS-2024-005": 0.86   # Ananya: Consistent (~86%)
    }

    start_date = date.today() - timedelta(weeks=weeks)
    total_raw_records = 0
    raw_logs_batch = []

    current_date = start_date
    while current_date <= date.today():
        day_name = current_date.strftime("%A")
        day_sessions = [s for s in sessions if s.day_of_week == day_name]

        for sess in day_sessions:
            for student in students:
                base_prob = student_archetypes.get(student.student_id_str, 0.80)

                if day_name == "Friday":
                    base_prob -= 0.08

                if random.random() < base_prob:
                    is_late = random.random() < 0.10
                    offset_min = random.randint(11, 20) if is_late else random.randint(-5, 8)
                    
                    s_time = sess.start_time
                    if isinstance(s_time, str):
                        s_time = datetime.strptime(s_time.split(".")[0], "%H:%M:%S").time()

                    scan_dt = datetime.combine(current_date, s_time) + timedelta(minutes=offset_min)

                    raw_log = RawAttendanceLog(
                        raw_device_id=f"DEV-{sess.room_number}",
                        student_id_str=student.student_id_str,
                        scan_timestamp=scan_dt,
                        scan_method=random.choice(["QR_CODE", "RFID", "BIOMETRIC"]),
                        room_code=sess.room_number,
                        device_ip_or_geo=f"192.168.10.{random.randint(10, 200)}",
                        processing_status="PENDING"
                    )
                    raw_logs_batch.append(raw_log)
                    total_raw_records += 1

        if len(raw_logs_batch) >= 200:
            session.bulk_save_objects(raw_logs_batch)
            session.commit()
            raw_logs_batch = []

        current_date += timedelta(days=1)

    if raw_logs_batch:
        session.bulk_save_objects(raw_logs_batch)
        session.commit()

    print(f"[DATA GEN] Generated {total_raw_records} raw attendance logs for Smt. C.H.M. College.")
    return total_raw_records


seed_hierarchy_and_academics = seed_chmc_academics
seed_user_accounts = seed_chmc_user_accounts
generate_raw_attendance_stream = generate_chmc_attendance_stream


def run_full_seed():
    drop_db()
    init_db()
    with get_db_session() as session:
        seed_chmc_academics(session)
        seed_chmc_user_accounts(session)
        generate_chmc_attendance_stream(session, weeks=8)


if __name__ == "__main__":
    run_full_seed()
