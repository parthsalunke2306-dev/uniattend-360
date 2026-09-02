"""
Unit and Integration Tests for UniAttend 360 Data Sync Bridge.
Verifies bidirectional synchronization between offline client cache and PostgreSQL/SQLite database.
"""

import pytest
from fastapi.testclient import TestClient
from api.server import app
from database.db_manager import get_db_session
from database.models import UserAccount, Student, SecurityAuditLog

client = TestClient(app)


def test_sync_status_endpoint():
    """Verify that sync status endpoint returns online status and DB metrics."""
    response = client.get("/api/v1/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] == "connected"
    assert data["total_user_accounts"] >= 1


def test_sync_client_state_device_binding_and_audit():
    """Verify that offline client profiles and audit logs sync to database."""
    payload = {
        "profiles": {
            "chmc.ds.2024.002": {
                "name": "Aarav Sharma",
                "email": "aarav.sharma@chmc.edu",
                "role": "STUDENT",
                "is_device_bound": True,
                "device_name": "OnePlus 11 5G (Enclave)",
                "device_fingerprint": "DEV-SYNC-ENCLAVE-9988",
                "must_change_password": False
            },
            "chmc.ds.2024.777": {
                "name": "Offline Provisioned Student",
                "email": "sync.student.777@chmc.edu",
                "role": "STUDENT",
                "initial_password": "OfflinePassword@2026",
                "must_change_password": True,
                "is_device_bound": False
            }
        },
        "audit_logs": [
            {
                "event": "OFFLINE_TEST_AUDIT_LOG",
                "actor": "Mr. Sanjay Mehta (Admin Office)",
                "target": "chmc.ds.2024.777",
                "severity": "INFO",
                "details": "Offline student provisioned during connectivity drop."
            }
        ]
    }

    response = client.post("/api/v1/sync/client-state", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert "chmc.ds.2024.002" in res_data["synced_users"]
    assert res_data["synced_logs_count"] == 1

    # Verify state in database
    with get_db_session() as session:
        aarav = session.query(UserAccount).filter_by(username="chmc.ds.2024.002").first()
        assert aarav is not None
        assert aarav.is_device_bound is True
        assert aarav.bound_device_name == "OnePlus 11 5G (Enclave)"
        assert aarav.bound_device_uuid == "DEV-SYNC-ENCLAVE-9988"
        assert aarav.must_change_password is False

        new_st = session.query(UserAccount).filter_by(username="chmc.ds.2024.777").first()
        assert new_st is not None
        assert new_st.role == "STUDENT"
        assert new_st.email == "sync.student.777@chmc.edu"
