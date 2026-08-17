"""
Role-Based Access Control (RBAC) & Profile Categorization Engine.
Defines role permissions, view boundaries, and profile switchers for:
  1. Principal (Campus/University Executive)
  2. Departmental Head (HOD - Department Executive)
  3. Teachers / Faculty (Classroom & Session Master)
  4. Students (Mobile Check-In & Academic 360)
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from database.models import UserAccount, Department, Course, Faculty, Student, University


ROLE_DEFINITIONS = {
    "PRINCIPAL": {
        "title": "Principal & Vice Chancellor",
        "icon": "🏛️",
        "badge_color": "#1E3A8A",
        "description": "Executive oversight across all colleges, departments, faculty performance, and university-wide defaulter audits.",
        "permissions": {
            "view_all_departments": True,
            "view_campus_kpis": True,
            "manage_departments": True,
            "export_university_reports": True,
            "open_kiosk": True,
            "view_student_simulator": True,
            "audit_proxy_radar": True
        }
    },
    "HOD": {
        "title": "Departmental Head (HOD)",
        "icon": "👔",
        "badge_color": "#0284C7",
        "description": "Department-level management, faculty lecture regularity, subject-wise defaulter approval, and parent intimation notices.",
        "permissions": {
            "view_all_departments": False,
            "view_campus_kpis": True,
            "manage_departments": False,
            "export_university_reports": True,
            "open_kiosk": True,
            "view_student_simulator": True,
            "audit_proxy_radar": True
        }
    },
    "TEACHER": {
        "title": "Teacher / Faculty",
        "icon": "👨‍🏫",
        "badge_color": "#059669",
        "description": "Classroom session instructor, live rotating QR kiosk broadcaster, real-time digital roster management, and manual override.",
        "permissions": {
            "view_all_departments": False,
            "view_campus_kpis": False,
            "manage_departments": False,
            "export_university_reports": False,
            "open_kiosk": True,
            "view_student_simulator": True,
            "audit_proxy_radar": True
        }
    },
    "STUDENT": {
        "title": "Student",
        "icon": "🎓",
        "badge_color": "#7C3AED",
        "description": "Mobile self-checkin, live GPS verification, subject-wise attendance tracking, 'What-If' exam eligibility simulator, and official warning letters.",
        "permissions": {
            "view_all_departments": False,
            "view_campus_kpis": False,
            "manage_departments": False,
            "export_university_reports": False,
            "open_kiosk": False,
            "view_student_simulator": True,
            "audit_proxy_radar": False
        }
    }
}


class ProfileManager:
    """Manages role-based views and persona state."""

    @staticmethod
    def get_role_info(role: str) -> Dict[str, Any]:
        return ROLE_DEFINITIONS.get(role, ROLE_DEFINITIONS["STUDENT"])

    @staticmethod
    def get_users_by_role(session: Session, role: str) -> List[UserAccount]:
        return session.query(UserAccount).filter_by(role=role).all()

    @staticmethod
    def get_user_context(session: Session, user_id: int) -> Dict[str, Any]:
        """Loads full institutional context for a logged-in user."""
        user = session.get(UserAccount, user_id)
        if not user:
            return {}

        role_info = ProfileManager.get_role_info(user.role)
        context = {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "role_title": role_info["title"],
            "role_icon": role_info["icon"],
            "badge_color": role_info["badge_color"],
            "permissions": role_info["permissions"],
            "university_id": user.university_id,
            "department_id": user.department_id,
            "faculty_id": user.faculty_id,
            "student_id": user.student_id,
        }

        # Attach associated objects
        if user.department_id:
            dept = session.get(Department, user.department_id)
            context["department_name"] = dept.name if dept else None
            context["dept_code"] = dept.dept_code if dept else None

        if user.faculty_id:
            fac = session.get(Faculty, user.faculty_id)
            context["faculty_designation"] = fac.designation if fac else None

        if user.student_id:
            st = session.get(Student, user.student_id)
            context["student_roll"] = st.student_id_str if st else None
            context["student_semester"] = st.semester if st else None

        return context
