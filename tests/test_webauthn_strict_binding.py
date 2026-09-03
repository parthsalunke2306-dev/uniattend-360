import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from api.server import app
from database.db_manager import get_db_session
from database.models import UserAccount, Passkey, Student, SecurityAuditLog
from api.security import create_jwt_access_token

client = TestClient(app)

@pytest.fixture
def test_student_and_admin():
    with get_db_session() as session:
        # 1. Admin Staff
        admin = session.query(UserAccount).filter_by(username="test_admin_staff").first()
        if not admin:
            admin = UserAccount(
                username="test_admin_staff",
                email="test_admin_staff@chmc.edu",
                full_name="Mr. Sanjay Mehta",
                role="ADMIN_STAFF",
                is_active=True
            )
            session.add(admin)
            session.flush()

        # 2. Student
        student_user = session.query(UserAccount).filter_by(username="test_binding_student").first()
        if not student_user:
            student_user = UserAccount(
                username="test_binding_student",
                email="test_binding_student@chmc.edu",
                full_name="Binding Test Student",
                role="STUDENT",
                is_active=True,
                is_device_bound=False,
                device_reset_status="NONE"
            )
            session.add(student_user)
            session.flush()

        admin_token = create_jwt_access_token(data={"sub": str(admin.id), "role": admin.role})
        session.commit()
        return {
            "student_username": student_user.username,
            "student_id": student_user.id,
            "admin_token": admin_token
        }


def test_passkey_db_unique_constraint(test_student_and_admin):
    """
    CRITICAL: Add a strict UNIQUE constraint on the user_id column in the passkeys table.
    The database itself must reject any attempt to insert a second passkey for a single user.
    """
    uid = test_student_and_admin["student_id"]
    with get_db_session() as session:
        # Clear any prior passkeys
        session.query(Passkey).filter_by(user_id=uid).delete()
        session.commit()

        # Insert first passkey
        pk1 = Passkey(
            user_id=uid,
            credential_id="cred_id_primary_phone_001",
            public_key="pubkey_test_base64_001",
            counter=0,
            device_name="Primary Android Phone"
        )
        session.add(pk1)
        session.commit()

        # Attempt to insert a second passkey for the same user_id
        pk2 = Passkey(
            user_id=uid,
            credential_id="cred_id_secondary_proxy_002",
            public_key="pubkey_test_base64_002",
            counter=0,
            device_name="Secondary Proxy Handset"
        )
        session.add(pk2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_generate_registration_options_403_when_device_already_registered(test_student_and_admin):
    """
    /generate-registration-options: Check if the user already exists in the passkeys table.
    If yes, return a 403 error ('Device already registered').
    """
    uname = test_student_and_admin["student_username"]
    uid = test_student_and_admin["student_id"]

    with get_db_session() as session:
        u = session.query(UserAccount).filter_by(id=uid).first()
        u.is_device_bound = True
        session.commit()

    # Request options for user that already has a registered device
    response = client.post("/generate-registration-options", json={"identifier": uname})
    assert response.status_code == 403
    assert "Device already registered" in response.json()["detail"]


def test_generate_registration_options_success_for_new_device(test_student_and_admin):
    uname = test_student_and_admin["student_username"]
    uid = test_student_and_admin["student_id"]

    with get_db_session() as session:
        session.query(Passkey).filter_by(user_id=uid).delete()
        u = session.query(UserAccount).filter_by(id=uid).first()
        u.is_device_bound = False
        session.commit()

    response = client.post("/generate-registration-options", json={"identifier": uname})
    assert response.status_code == 200
    data = response.json()
    assert "challenge" in data
    assert "rp" in data or "rpId" in data


def test_verify_registration_and_db_binding(test_student_and_admin):
    uname = test_student_and_admin["student_username"]
    uid = test_student_and_admin["student_id"]

    # First call generate options to initialize challenge
    client.post("/generate-registration-options", json={"identifier": uname})

    # Verify registration
    verify_resp = client.post("/verify-registration", json={
        "identifier": uname,
        "credential": {"id": "mock_cred_uuid_12345", "rawId": "mock_cred_uuid_12345"},
        "device_name": "Samsung Galaxy S24"
    })
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "SUCCESS"

    with get_db_session() as session:
        u = session.query(UserAccount).filter_by(id=uid).first()
        assert u.is_device_bound is True
        assert u.device_reset_status == "NONE"
        pk = session.query(Passkey).filter_by(user_id=uid).first()
        assert pk is not None
        assert pk.credential_id == "mock_cred_uuid_12345"
        assert pk.counter == 0


def test_generate_authentication_options_retrieves_user_credential(test_student_and_admin):
    uname = test_student_and_admin["student_username"]
    resp = client.post("/generate-authentication-options", json={"identifier": uname})
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data
    assert "allowCredentials" in data
    # Enforces 1:1 hardware device
    allow_creds = data["allowCredentials"]
    assert len(allow_creds) >= 1
    assert any("mock_cred_uuid_12345" in str(c.get("id")) for c in allow_creds)


def test_verify_authentication_increments_counter(test_student_and_admin):
    uname = test_student_and_admin["student_username"]
    uid = test_student_and_admin["student_id"]

    client.post("/generate-authentication-options", json={"identifier": uname})

    auth_resp = client.post("/verify-authentication", json={
        "identifier": uname,
        "credential": {"id": "mock_cred_uuid_12345"}
    })
    assert auth_resp.status_code == 200
    assert auth_resp.json()["verified"] is True

    with get_db_session() as session:
        pk = session.query(Passkey).filter_by(user_id=uid).first()
        assert pk.counter >= 1
        assert pk.last_used_at is not None


def test_student_device_reset_request(test_student_and_admin):
    uname = test_student_and_admin["student_username"]
    uid = test_student_and_admin["student_id"]

    resp = client.post("/request-device-reset", json={
        "identifier": uname,
        "reason": "Lost smartphone on local train"
    })
    assert resp.status_code == 200
    assert resp.json()["device_reset_status"] == "PENDING"

    with get_db_session() as session:
        u = session.query(UserAccount).filter_by(id=uid).first()
        assert u.device_reset_status == "PENDING"


def test_admin_pending_resets_queue(test_student_and_admin):
    admin_token = test_student_and_admin["admin_token"]
    resp = client.get("/admin/pending-resets", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    list_items = resp.json()
    assert any(item["username"] == test_student_and_admin["student_username"] for item in list_items)


def test_admin_approve_reset_transaction(test_student_and_admin):
    uname = test_student_and_admin["student_username"]
    uid = test_student_and_admin["student_id"]
    admin_token = test_student_and_admin["admin_token"]

    resp = client.post("/admin/approve-reset", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "student_id_str": uname,
        "reason": "Verified police FIR for lost phone"
    })
    assert resp.status_code == 200
    assert resp.json()["device_reset_status"] == "NONE"
    assert resp.json()["is_device_bound"] is False

    with get_db_session() as session:
        u = session.query(UserAccount).filter_by(id=uid).first()
        assert u.is_device_bound is False
        assert u.device_reset_status == "NONE"
        assert u.bound_device_name is None
        pk_count = session.query(Passkey).filter_by(user_id=uid).count()
        assert pk_count == 0


def test_admin_reject_reset(test_student_and_admin):
    uname = test_student_and_admin["student_username"]
    uid = test_student_and_admin["student_id"]
    admin_token = test_student_and_admin["admin_token"]

    # Student requests reset again
    client.post("/request-device-reset", json={"identifier": uname, "reason": "Testing reject"})

    # Admin rejects
    resp = client.post("/admin/reject-reset", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "student_id_str": uname,
        "reason": "Unsubstantiated request"
    })
    assert resp.status_code == 200
    assert resp.json()["device_reset_status"] == "NONE"

    with get_db_session() as session:
        u = session.query(UserAccount).filter_by(id=uid).first()
        assert u.device_reset_status == "NONE"
