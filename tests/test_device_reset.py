import pytest
from fastapi.testclient import TestClient
from api.server import app
from database.db_manager import get_db_session
from database.models import UserAccount, UserPasskey

client = TestClient(app)

def test_admin_device_reset_purges_passkeys_and_unlinks_device():
    with get_db_session() as session:
        user = session.query(UserAccount).filter_by(username='test.reset.student').first()
        if not user:
            user = UserAccount(
                username='test.reset.student',
                email='test.reset.student@chmc.edu',
                full_name='Reset Test Student',
                role='STUDENT',
                is_active=True,
                is_device_bound=True,
                bound_device_name='Old iPhone 12',
                bound_device_uuid='DEV-OLD-IPHONE-UUID'
            )
            session.add(user)
            session.flush()

        user.is_device_bound = True
        user.bound_device_name = 'Old iPhone 12'
        user.bound_device_uuid = 'DEV-OLD-IPHONE-UUID'

        existing_pk = session.query(UserPasskey).filter_by(user_id=user.id).first()
        if not existing_pk:
            pk = UserPasskey(
                user_id=user.id,
                credential_id='test-cred-id-old-phone',
                public_key='MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A',
                device_name='Old iPhone 12 Passkey'
            )
            session.add(pk)
        session.commit()

    response = client.post('/api/v1/attendance/device/reset', json={
        'student_id_str': 'test.reset.student',
        'authorized_by': 'Mr. Sanjay Mehta (Admin Staff)',
        'reason': 'Lost old iPhone, purchased new handset'
    })

    assert response.status_code == 200
    data = response.json()
    assert data.get('db_reset') is True
    assert data.get('status') == 'RESET_SUCCESSFUL'

    with get_db_session() as session:
        user = session.query(UserAccount).filter_by(username='test.reset.student').first()
        assert user is not None
        assert user.is_device_bound is False
        assert user.bound_device_name is None
        assert user.bound_device_uuid is None

        passkey_count = session.query(UserPasskey).filter_by(user_id=user.id).count()
        assert passkey_count == 0

        session.delete(user)
        session.commit()
