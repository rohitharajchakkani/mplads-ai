"""Phase 11 uses live monitoring evidence but removes verification-only workflow rows."""
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import create_session_factory
from app.core.config import get_settings
from app.main import app
from app.models.review import ReviewCase, ReviewCaseEvent, ReviewCaseEvidenceSnapshot, ReviewEscalation, ReviewNotification

client = TestClient(app)
AUTHOR = {"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "phase11-test-author"}


def cleanup(case_id: str) -> None:
    with create_session_factory(get_settings().database_url)() as db:
        case = db.get(ReviewCase, case_id)
        if case is None:
            return
        db.execute(delete(ReviewNotification).where(ReviewNotification.case_id == case_id))
        db.execute(delete(ReviewEscalation).where(ReviewEscalation.case_id == case_id))
        db.execute(delete(ReviewCaseEvent).where(ReviewCaseEvent.case_id == case_id))
        db.execute(delete(ReviewCaseEvidenceSnapshot).where(ReviewCaseEvidenceSnapshot.snapshot_id == case.evidence_snapshot_id))
        db.delete(case)
        db.commit()


def test_review_case_freezes_real_evidence_enforces_transitions_and_scope():
    preflight = client.options("/api/v1/reviews/cases", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "X-MPLADS-Role, X-MPLADS-Actor"})
    assert preflight.status_code == 200
    assert "x-mplads-actor" in preflight.headers["access-control-allow-headers"].lower()
    alert = client.get("/api/v1/alerts?limit=1", headers=AUTHOR).json()[0]
    created = client.post("/api/v1/reviews/cases", headers=AUTHOR, json={"alert_id": alert["alert_id"]})
    assert created.status_code == 201
    case = created.json()
    case_id = case["case_id"]
    try:
        initial = client.get(f"/api/v1/reviews/cases/{case_id}", headers=AUTHOR)
        assert initial.status_code == 200
        frozen_evidence = initial.json()["evidence_snapshot"]

        wrong_scope = client.get(f"/api/v1/reviews/cases/{case_id}", headers={"X-MPLADS-Role": "STATE_NODAL_AUTHORITY", "X-MPLADS-State-Scope": "Not an authorized state"})
        assert wrong_scope.status_code == 404

        def action(name: str, extra: dict):
            nonlocal case
            response = client.post(f"/api/v1/reviews/cases/{case_id}/{name}", headers=AUTHOR, json={"version": case["version"], **extra})
            assert response.status_code == 200, response.text
            case = response.json()

        action("assign", {"assignee": "phase11-test-assignee"})
        notifications = client.get("/api/v1/notifications", headers={"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "phase11-test-assignee"})
        assert notifications.status_code == 200 and any(item["case_id"] == case_id for item in notifications.json())
        action("start-review", {})
        action("comment", {"comment": "A source-backed review note."})
        action("request-follow-up", {"reason": "Confirm the available source context."})
        action("start-review", {})
        action("resolve", {"resolution_type": "INFORMATION_VERIFIED", "resolution_note": "Review complete against frozen evidence."})
        action("close", {})
        action("reopen", {})
        stale = client.post(f"/api/v1/reviews/cases/{case_id}/comment", headers=AUTHOR, json={"version": 1, "comment": "stale"})
        assert stale.status_code == 409
        detail = client.get(f"/api/v1/reviews/cases/{case_id}", headers=AUTHOR).json()
        assert detail["evidence_snapshot"] == frozen_evidence
        assert [event["action"] for event in detail["events"]] == ["CREATED", "ASSIGNED", "UNDER_REVIEW_STARTED", "COMMENTED", "FOLLOW_UP_REQUESTED", "UNDER_REVIEW_STARTED", "RESOLVED", "CLOSED", "REOPENED"]
    finally:
        cleanup(case_id)
