"""
Multi-Tenant Synthetic Data Generator for UniAttend Analytics.
Simulates realistic universities, departments, courses, faculty, students,
weekly class timetables, and raw IoT/RFID/QR attendance scan logs with edge cases.
"""

import random
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Tuple
from faker import Faker
from sqlalchemy.orm import Session

from database.models import (
    University, College, Department, Course, Faculty, Student, 
    TimetableSession, RawAttendanceLog, UserAccount
)
from database.db_manager import get_db_session, init_db

fake = Faker()
Faker.seed(42)
random.seed(42)


# ==========================================
# INSTITUTIONAL SEED CONFIGURATIONS
# ==========================================

UNIVERSITIES_CONFIG = [
    {
        "name": "Apex National University",
        "code": "ANU",
        "colleges": [
            {
                "name": "College of Engineering & Technology",
                "campus_code": "ANU-ENG",
                "city": "Boston",
                "departments": [
                    {
                        "name": "Computer Science & Engineering",
                        "code": "CSE",
                        "courses": [
                            ("Distributed Systems", "CS401", 4, 1),
                            ("Data Engineering Pipelines", "CS402", 4, 1),
                            ("Advanced Database Systems", "CS403", 3, 1),
                            ("Cloud Computing Architecture", "CS404", 3, 1),
                        ]
                    },
                    {
                        "name": "Data Science & Artificial Intelligence",
                        "code": "DSAI",
                        "courses": [
                            ("Machine Learning Engineering", "DS501", 4, 1),
                            ("Deep Learning & LLMs", "DS502", 4, 1),
                            ("Big Data Infrastructure", "DS503", 3, 1),
                            ("Statistical Data Analysis", "DS504", 3, 1),
                        ]
                    }
                ]
            },
            {
                "name": "School of Management & Analytics",
                "campus_code": "ANU-MGT",
                "city": "Boston",
                "departments": [
                    {
                        "name": "Business Analytics",
                        "code": "BA",
                        "courses": [
                            ("Business Intelligence Systems", "BA301", 3, 1),
                            ("Predictive Marketing Analytics", "BA302", 3, 1),
                            ("Supply Chain Optimization", "BA303", 3, 1),
                        ]
                    }
                ]
            }
        ]
    },
    {
        "name": "Metro Institute of Technology",
        "code": "MIT-TECH",
        "colleges": [
            {
                "name": "Institute of Informatics",
                "campus_code": "MIT-INFO",
                "city": "Seattle",
                "departments": [
                    {
                        "name": "Software Engineering",
                        "code": "SE",
                        "courses": [
                            ("Microservices Architecture", "SE601", 4, 1),
                            ("DevOps & CI/CD Pipelines", "SE602", 3, 1),
                            ("System Security & Compliance", "SE603", 3, 1),
                        ]
                    }
                ]
            }
        ]
    }
]

ROOMS = ["LH-101", "LH-102", "CS-LAB-A", "CS-LAB-B", "AUD-1", "SE-204", "AI-LAB"]
SCAN_METHODS = ["RFID", "QR_CODE", "BIOMETRIC", "FACIAL_RECOGNITION"]
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

TIME_SLOTS = [
    (time(9, 0), time(10, 0)),
    (time(10, 15), time(11, 15)),
    (time(11, 30), time(12, 30)),
    (time(13, 30), time(14, 30)),
    (time(14, 45), time(15, 45)),
]


def seed_hierarchy_and_academics(session: Session) -> Dict[str, list]:
    """Populates Universities, Colleges, Departments, Courses, Faculty, and Students."""
    all_students = []
    all_courses = []
    all_sessions = []

    print("[DATA GEN] Seeding Academic Hierarchy...")

    for u_cfg in UNIVERSITIES_CONFIG:
        uni = session.query(University).filter_by(code=u_cfg["code"]).first()
        if not uni:
            uni = University(name=u_cfg["name"], code=u_cfg["code"])
            session.add(uni)
            session.flush()

        for c_cfg in u_cfg["colleges"]:
            college = session.query(College).filter_by(campus_code=c_cfg["campus_code"]).first()
            if not college:
                college = College(
                    university_id=uni.id,
                    name=c_cfg["name"],
                    campus_code=c_cfg["campus_code"],
                    city=c_cfg["city"]
                )
                session.add(college)
                session.flush()

            for d_cfg in c_cfg["departments"]:
                dept_code_unique = f"{c_cfg['campus_code']}-{d_cfg['code']}"
                dept = session.query(Department).filter_by(dept_code=dept_code_unique).first()
                if not dept:
                    dept = Department(
                        college_id=college.id,
                        name=d_cfg["name"],
                        dept_code=dept_code_unique
                    )
                    session.add(dept)
                    session.flush()

                # Seed Faculty for Department
                faculty_list = []
                for f_idx in range(4):
                    fac_id = f"FAC-{dept.dept_code}-{f_idx+1:02d}"
                    fac = session.query(Faculty).filter_by(faculty_id_str=fac_id).first()
                    if not fac:
                        fac = Faculty(
                            department_id=dept.id,
                            faculty_id_str=fac_id,
                            full_name=f"Prof. {fake.first_name()} {fake.last_name()}",
                            email=f"prof.{fac_id.lower()}@{uni.code.lower()}.edu",
                            designation=random.choice(["Professor", "Associate Professor", "Assistant Professor"])
                        )
                        session.add(fac)
                        session.flush()
                    faculty_list.append(fac)

                # Seed Courses
                dept_courses = []
                for c_name, c_code, credits, sem in d_cfg["courses"]:
                    full_code = f"{d_cfg['code']}-{c_code}"
                    course = session.query(Course).filter_by(course_code=full_code).first()
                    if not course:
                        course = Course(
                            department_id=dept.id,
                            course_name=c_name,
                            course_code=full_code,
                            credits=credits,
                            semester=sem,
                            minimum_attendance_pct=75.0
                        )
                        session.add(course)
                        session.flush()
                    dept_courses.append(course)
                    all_courses.append(course)

                # Seed Timetable Sessions for each course
                for c_idx, course in enumerate(dept_courses):
                    # 2-3 sessions per week per course
                    assigned_days = random.sample(DAYS_OF_WEEK, 3)
                    assigned_faculty = faculty_list[c_idx % len(faculty_list)]
                    room = random.choice(ROOMS)

                    for day in assigned_days:
                        slot = random.choice(TIME_SLOTS)
                        session_obj = session.query(TimetableSession).filter_by(
                            course_id=course.id, day_of_week=day, start_time=slot[0]
                        ).first()
                        if not session_obj:
                            session_obj = TimetableSession(
                                course_id=course.id,
                                faculty_id=assigned_faculty.id,
                                room_number=room,
                                day_of_week=day,
                                start_time=slot[0],
                                end_time=slot[1],
                                session_type="Lecture" if "LAB" not in room else "Lab"
                            )
                            session.add(session_obj)
                            session.flush()
                        all_sessions.append(session_obj)

                # Seed Students in Department (30 students per department)
                for s_idx in range(1, 31):
                    roll_no = f"{dept.dept_code}-2024-{s_idx:03d}"
                    student = session.query(Student).filter_by(student_id_str=roll_no).first()
                    if not student:
                        student = Student(
                            department_id=dept.id,
                            student_id_str=roll_no,
                            full_name=fake.name(),
                            email=f"{roll_no.lower()}@{uni.code.lower()}.edu",
                            batch_year=2024,
                            semester=1,
                            rfid_card_id=f"RFID-{fake.hexify(text='^^^^^^^^^^').upper()}"
                        )
                        session.add(student)
                        session.flush()
                    all_students.append(student)

    session.commit()
    print(f"[DATA GEN] Successfully seeded {len(all_students)} students, {len(all_courses)} courses, and {len(all_sessions)} sessions.")
    return {
        "students": all_students,
        "courses": all_courses,
        "sessions": all_sessions
    }


def generate_raw_attendance_stream(session: Session, weeks: int = 8) -> int:
    """
    Simulates raw device swipe events across a semester timeline (e.g. 8 weeks).
    Embeds realistic student behavioral archetypes and device noise:
      - Archetype 1: Exemplary (~95% attendance probability)
      - Archetype 2: Consistent (~85% attendance probability)
      - Archetype 3: Borderline/Slacker (~73% attendance probability - at risk)
      - Archetype 4: Chronic Defaulter (~50% attendance probability)
      - Noise: Double swipes within 10 seconds, late check-ins, proxy attempts in wrong rooms.
    """
    print(f"[DATA GEN] Simulating raw attendance sensor logs for {weeks} academic weeks...")

    # Fetch all timetable sessions and active students
    all_sessions: List[TimetableSession] = session.query(TimetableSession).all()
    all_students: List[Student] = session.query(Student).all()

    if not all_sessions or not all_students:
        print("[DATA GEN] No sessions or students found. Run seed_hierarchy_and_academics first.")
        return 0

    # Assign attendance behavioral profiles to students
    student_profiles = {}
    for s in all_students:
        rand_val = random.random()
        if rand_val < 0.40:
            student_profiles[s.id] = {"base_prob": 0.95, "archetype": "EXEMPLARY"}
        elif rand_val < 0.70:
            student_profiles[s.id] = {"base_prob": 0.84, "archetype": "CONSISTENT"}
        elif rand_val < 0.88:
            student_profiles[s.id] = {"base_prob": 0.72, "archetype": "BORDERLINE"}
        else:
            student_profiles[s.id] = {"base_prob": 0.48, "archetype": "CHRONIC_DEFAULTER"}

    # Map department to students
    dept_students: Dict[int, List[Student]] = {}
    for s in all_students:
        dept_students.setdefault(s.department_id, []).append(s)

    start_date = date.today() - timedelta(weeks=weeks)
    total_raw_records = 0
    raw_logs_batch = []

    day_name_to_int = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4
    }

    # Iterate day by day
    current_date = start_date
    end_date = date.today()

    while current_date <= end_date:
        weekday_idx = current_date.weekday()
        if weekday_idx in [5, 6]:  # Skip Saturday and Sunday
            current_date += timedelta(days=1)
            continue

        day_name = list(day_name_to_int.keys())[weekday_idx]
        daily_sessions = [sess for sess in all_sessions if sess.day_of_week == day_name]

        for sess in daily_sessions:
            course = sess.course
            enrolled_students = dept_students.get(course.department_id, [])

            for student in enrolled_students:
                profile = student_profiles[student.id]
                base_prob = profile["base_prob"]

                # Friday slump effect
                if day_name == "Friday":
                    base_prob -= 0.08
                # Morning 9 AM slump effect
                if sess.start_time.hour == 9:
                    base_prob -= 0.05

                # Decide if student attended
                attended = random.random() < max(0.1, base_prob)

                if attended:
                    # Realistic scan time (within 10 mins before or 15 mins after class start)
                    start_dt = datetime.combine(current_date, sess.start_time)
                    jitter_minutes = random.randint(-8, 12)
                    scan_dt = start_dt + timedelta(minutes=jitter_minutes, seconds=random.randint(0, 59))
                    scan_method = random.choices(SCAN_METHODS, weights=[0.6, 0.25, 0.1, 0.05])[0]

                    raw_log = RawAttendanceLog(
                        raw_device_id=f"DEV-{sess.room_number}",
                        student_id_str=student.student_id_str,
                        scan_timestamp=scan_dt,
                        scan_method=scan_method,
                        room_code=sess.room_number,
                        device_ip_or_geo=f"192.168.10.{random.randint(10, 200)}",
                        processing_status="PENDING"
                    )
                    raw_logs_batch.append(raw_log)
                    total_raw_records += 1

                    # 3% chance of intentional duplicate scan (double tap within 5 seconds)
                    if random.random() < 0.03:
                        dup_log = RawAttendanceLog(
                            raw_device_id=f"DEV-{sess.room_number}",
                            student_id_str=student.student_id_str,
                            scan_timestamp=scan_dt + timedelta(seconds=random.randint(2, 6)),
                            scan_method=scan_method,
                            room_code=sess.room_number,
                            device_ip_or_geo=f"192.168.10.{random.randint(10, 200)}",
                            processing_status="PENDING"
                        )
                        raw_logs_batch.append(dup_log)
                        total_raw_records += 1

                    # 1.5% chance of proxy scan anomaly (Student card scanned in another room at same time)
                    if random.random() < 0.015:
                        other_room = random.choice([r for r in ROOMS if r != sess.room_number])
                        proxy_log = RawAttendanceLog(
                            raw_device_id=f"DEV-{other_room}",
                            student_id_str=student.student_id_str,
                            scan_timestamp=scan_dt + timedelta(minutes=random.randint(1, 3)),
                            scan_method=scan_method,
                            room_code=other_room,
                            device_ip_or_geo=f"192.168.20.{random.randint(10, 200)}",
                            processing_status="PENDING"
                        )
                        raw_logs_batch.append(proxy_log)
                        total_raw_records += 1

        # Commit in chunks of 1000
        if len(raw_logs_batch) >= 1000:
            session.bulk_save_objects(raw_logs_batch)
            session.commit()
            raw_logs_batch = []

        current_date += timedelta(days=1)

    if raw_logs_batch:
        session.bulk_save_objects(raw_logs_batch)
        session.commit()

    print(f"[DATA GEN] Generated and inserted {total_raw_records} raw attendance logs into Bronze layer.")
    return total_raw_records


def seed_user_accounts(session: Session):
    """Populates user profiles for Principal, Departmental Heads (HODs), Teachers, and Students."""
    print("[DATA GEN] Seeding Role-Based User Accounts (Principal, HOD, Teacher, Student)...")

    universities = session.query(University).all()
    for uni in universities:
        # 1. Principal / Chancellor
        p_uname = f"principal.{uni.code.lower()}"
        p_user = session.query(UserAccount).filter_by(username=p_uname).first()
        if not p_user:
            p_user = UserAccount(
                username=p_uname,
                email=f"principal@{uni.code.lower()}.edu",
                full_name=f"Dr. Arthur Vance (Principal & Chancellor, {uni.name})",
                role="PRINCIPAL",
                university_id=uni.id,
                avatar_icon="🏛️"
            )
            session.add(p_user)

    departments = session.query(Department).all()
    for dept in departments:
        # 2. Departmental Head (HOD)
        h_uname = f"hod.{dept.dept_code.lower()}"
        h_user = session.query(UserAccount).filter_by(username=h_uname).first()
        if not h_user:
            h_user = UserAccount(
                username=h_uname,
                email=f"hod.{dept.dept_code.lower()}@{dept.college.university.code.lower()}.edu",
                full_name=f"Dr. Robert Miller (HOD, {dept.name})",
                role="HOD",
                university_id=dept.college.university_id,
                department_id=dept.id,
                avatar_icon="👔"
            )
            session.add(h_user)

    # 3. Faculty / Teachers
    all_faculty = session.query(Faculty).all()
    for fac in all_faculty:
        f_uname = fac.faculty_id_str.lower().replace("-", ".")
        f_user = session.query(UserAccount).filter_by(username=f_uname).first()
        if not f_user:
            f_user = UserAccount(
                username=f_uname,
                email=fac.email,
                full_name=fac.full_name,
                role="TEACHER",
                university_id=fac.department.college.university_id,
                department_id=fac.department_id,
                faculty_id=fac.id,
                avatar_icon="👨‍🏫"
            )
            session.add(f_user)

    # 4. Students
    all_students = session.query(Student).all()
    for st in all_students:
        s_uname = st.student_id_str.lower().replace("-", ".")
        s_user = session.query(UserAccount).filter_by(username=s_uname).first()
        if not s_user:
            s_user = UserAccount(
                username=s_uname,
                email=st.email,
                full_name=st.full_name,
                role="STUDENT",
                university_id=st.department.college.university_id,
                department_id=st.department_id,
                student_id=st.id,
                avatar_icon="🎓"
            )
            session.add(s_user)

    session.commit()
    print("[DATA GEN] User accounts seeded successfully.")


def run_full_seed():
    """Initializes the database and runs full data generation."""
    init_db()
    with get_db_session() as session:
        seed_hierarchy_and_academics(session)
        seed_user_accounts(session)
        generate_raw_attendance_stream(session, weeks=10)


if __name__ == "__main__":
    run_full_seed()
