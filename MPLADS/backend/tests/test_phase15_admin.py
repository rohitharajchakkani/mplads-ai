"""Administration is server-protected, real-state-backed, and auditable."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import create_session_factory
from app.main import app
from app.models.admin import AccessRequest


client = TestClient(app)
ADMIN = {"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "phase15-admin-test"}
STATE = {
    "X-MPLADS-Role": "STATE_NODAL_AUTHORITY",
    "X-MPLADS-State-Scope": "Test State",
    "X-MPLADS-Actor": "phase15-state-test",
}


def _request(request_id: str, name: str = "Test applicant") -> None:
    session = create_session_factory(get_settings().database_url)()
    try:
        session.add(
            AccessRequest(
                request_id=request_id,
                name=name,
                designation="Test designation",
                office="Test office",
                state_name="Test State",
                district_or_ida="Test District",
                reason="Synthetic isolated-test access request.",
                status="PENDING",
                created_at=datetime.now(UTC),
                decided_at=None,
                decided_by=None,
                decision_note=None,
                approved_user_id=None,
            )
        )
        session.commit()
    finally:
        session.close()


def test_admin_routes_require_platform_administrator_and_do_not_trust_scope_headers():
    assert client.get("/api/v1/admin/system").status_code == 401
    assert client.get("/api/v1/admin/users?role=PLATFORM_ADMINISTRATOR").status_code == 401
    assert client.get("/api/v1/admin/access-requests?role=PLATFORM_ADMINISTRATOR").status_code == 401
    for path in (
        "/api/v1/admin/access-requests",
        "/api/v1/admin/users",
        "/api/v1/admin/datasets/versions",
        "/api/v1/admin/datasets/active",
        "/api/v1/admin/data-quality",
        "/api/v1/admin/data-quality/findings",
        "/api/v1/admin/audit-logs",
        "/api/v1/admin/system",
        "/api/v1/admin/configuration",
    ):
        assert client.get(path, headers=STATE).status_code == 403
    assert client.post(
        "/api/v1/admin/datasets/rollback",
        headers={"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR"},
        json={"confirmation": "ROLLBACK"},
    ).status_code == 403
    response = client.get("/api/v1/admin/system", headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["database_status"] == "OK"


def test_access_approval_requires_explicit_assignment_creates_user_and_audits():
    request_id = "access_phase15_approve"
    _request(request_id)
    listing = client.get("/api/v1/admin/access-requests?status=PENDING&state=Test%20State", headers=ADMIN)
    assert listing.status_code == 200
    assert any(row["request_id"] == request_id for row in listing.json()["items"])

    denied = client.post(
        f"/api/v1/admin/access-requests/{request_id}/approve",
        headers=STATE,
        json={"role": "STATE_NODAL_AUTHORITY", "state_scope": "Test State", "confirmation": "APPROVE"},
    )
    assert denied.status_code == 403
    approved = client.post(
        f"/api/v1/admin/access-requests/{request_id}/approve",
        headers=ADMIN,
        json={"role": "STATE_NODAL_AUTHORITY", "state_scope": "Test State", "confirmation": "APPROVE"},
    )
    assert approved.status_code == 200
    user = approved.json()
    assert user["role"] == "STATE_NODAL_AUTHORITY"
    assert user["state_scope"] == "Test State"
    assert user["district_scope"] is None and user["mp_scope"] is None

    audit = client.get("/api/v1/admin/audit-logs?event_type=ACCESS_REQUEST_APPROVED", headers=ADMIN)
    assert audit.status_code == 200
    assert any(row["entity_id"] == request_id for row in audit.json()["items"])
    assert "Synthetic isolated-test" not in str(audit.json())

    invalid_scope = client.patch(
        f"/api/v1/admin/users/{user['user_id']}",
        headers=ADMIN,
        json={
            "role": "MINISTRY",
            "state_scope": "Test State",
            "district_scope": None,
            "mp_scope": None,
            "expected_version": user["version"],
            "confirmation": "UPDATE_ACCESS",
        },
    )
    assert invalid_scope.status_code == 422

    missing_confirmation = client.patch(
        f"/api/v1/admin/users/{user['user_id']}",
        headers=ADMIN,
        json={"expected_version": user["version"]},
    )
    assert missing_confirmation.status_code == 422

    updated = client.patch(
        f"/api/v1/admin/users/{user['user_id']}",
        headers=ADMIN,
        json={
            "role": "MINISTRY",
            "state_scope": None,
            "district_scope": None,
            "mp_scope": None,
            "expected_version": user["version"],
            "confirmation": "UPDATE_ACCESS",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "MINISTRY"
    assert updated.json()["state_scope"] is None

    stale = client.patch(
        f"/api/v1/admin/users/{user['user_id']}",
        headers=ADMIN,
        json={"expected_version": user["version"], "confirmation": "UPDATE_ACCESS"},
    )
    assert stale.status_code == 409
    disabled = client.post(
        f"/api/v1/admin/users/{user['user_id']}/disable",
        headers=ADMIN,
        json={"expected_version": updated.json()["version"], "confirmation": "DISABLE", "reason": "Isolated test."},
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "DISABLED"


def test_rejection_dataset_quality_system_and_append_only_audit_surfaces():
    request_id = "access_phase15_reject"
    _request(request_id, name="Rejected test applicant")
    rejected = client.post(
        f"/api/v1/admin/access-requests/{request_id}/reject",
        headers=ADMIN,
        json={"confirmation": "REJECT", "decision_note": "Isolated test rejection."},
    )
    assert rejected.status_code == 200 and rejected.json()["status"] == "REJECTED"

    datasets = client.get("/api/v1/admin/datasets/versions", headers=ADMIN)
    assert datasets.status_code == 200
    assert datasets.json()["items"] and all(len(row["datasets"]) == 12 for row in datasets.json()["items"])
    active = client.get("/api/v1/admin/datasets/active", headers=ADMIN)
    assert active.status_code == 200 and active.json()["status"] == "ACTIVE"
    active_promotion = client.post(
        f"/api/v1/admin/datasets/releases/{active.json()['release_id']}/promote",
        headers=ADMIN,
        json={"confirmation": "PROMOTE"},
    )
    assert active_promotion.status_code == 409

    quality = client.get("/api/v1/admin/data-quality", headers=ADMIN)
    assert quality.status_code == 200
    assert "validation_warnings" in quality.json()["metrics"]
    findings = client.get("/api/v1/admin/data-quality/findings?page_size=5", headers=ADMIN)
    assert findings.status_code == 200 and findings.json()["pagination"]["page_size"] == 5

    system = client.get("/api/v1/admin/system", headers=ADMIN)
    configuration = client.get("/api/v1/admin/configuration", headers=ADMIN)
    assert system.status_code == configuration.status_code == 200
    assert "api_key" not in str(system.json()).lower()
    assert "database_url" not in str(system.json()).lower()
    assert configuration.json()["database"] == "CONFIGURED"

    audit = client.get("/api/v1/admin/audit-logs?page_size=100", headers=ADMIN)
    assert audit.status_code == 200 and audit.json()["items"]
    assert client.delete("/api/v1/admin/audit-logs", headers=ADMIN).status_code == 405
