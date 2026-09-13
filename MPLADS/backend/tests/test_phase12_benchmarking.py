"""Phase 12 assertions use persisted active-release benchmarks and clean action checks."""
from sqlalchemy import delete, func, select
from fastapi.testclient import TestClient

from app.benchmarking.engine import MIN_PEERS, MIN_VALID_WORKS, ensure_benchmark_run
from app.core.config import get_settings
from app.db.session import create_session_factory
from app.main import app
from app.models.benchmarking import BenchmarkResult, Recommendation, RecommendationEvent
from app.models.review import ReviewCase, ReviewCaseEvent, ReviewCaseEvidenceSnapshot, ReviewEscalation, ReviewNotification

client = TestClient(app)
AUTHOR = {"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "phase12-test-author"}


def _cleanup_case(case_id: str) -> None:
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


def test_same_house_peer_benchmarks_have_persisted_thresholds_and_provenance():
    with create_session_factory(get_settings().database_url)() as db:
        run = ensure_benchmark_run(db)
        assert run.status == "COMPLETED" and run.entity_count >= MIN_PEERS and run.result_count == run.entity_count * 3
        available = db.scalar(select(BenchmarkResult).where(BenchmarkResult.run_id == run.run_id, BenchmarkResult.benchmark_available.is_(True)))
        unavailable = db.scalar(select(BenchmarkResult).where(BenchmarkResult.run_id == run.run_id, BenchmarkResult.benchmark_available.is_(False)))
        assert available is not None and available.peer_count >= MIN_PEERS and available.valid_work_count >= MIN_VALID_WORKS
        assert available.p25 is not None and available.p75 is not None and available.p90 is not None and available.iqr == available.p75 - available.p25
        assert available.metric_details is not None
        completion = db.scalar(select(BenchmarkResult).where(BenchmarkResult.run_id == run.run_id, BenchmarkResult.metric == "COMPLETION_RATIO", BenchmarkResult.benchmark_available.is_(True)))
        assert completion is not None and completion.metric_details["numerator_completed_works"] <= completion.metric_details["denominator_sanctioned_works"]
        assert unavailable is not None and unavailable.unavailable_reason in {"Insufficient peer data", "Insufficient valid work observations"}

    payload = client.get("/api/v1/benchmarking/results?page=1&page_size=1", headers=AUTHOR).json()["items"][0]
    peers = client.get("/api/v1/benchmarking/peers", params={"result_id": payload["result_id"]}, headers=AUTHOR)
    assert peers.status_code == 200
    cohort = peers.json()
    assert cohort["cohort_definition"]["same_house"] is True
    assert payload["entity_id"] not in cohort["peer_ids"]
    assert len(cohort["peer_ids"]) == cohort["peer_count"]
    # State scope cannot obtain another state's benchmark by identifier (IDOR protection).
    denied = client.get(f"/api/v1/benchmarking/{payload['entity_type']}/{payload['entity_id']}", headers={"X-MPLADS-Role": "STATE_NODAL_AUTHORITY", "X-MPLADS-State-Scope": "Not an authorized state"})
    assert denied.status_code == 404


def test_recommendations_are_evidence_backed_status_versioned_and_can_open_review_case():
    response = client.get("/api/v1/recommendations?page=1&page_size=100", headers=AUTHOR)
    assert response.status_code == 200
    item = next(row for row in response.json()["items"] if "signal_id" in row["evidence_references"])
    original_status, original_version = item["status"], item["version"]
    recommendation_id = item["recommendation_id"]
    case_id = None
    try:
        changed = client.post(f"/api/v1/recommendations/{recommendation_id}/status", headers=AUTHOR, json={"status": "UNDER_REVIEW", "version": original_version})
        assert changed.status_code == 200 and changed.json()["version"] == original_version + 1
        conflict = client.post(f"/api/v1/recommendations/{recommendation_id}/status", headers=AUTHOR, json={"status": "RESOLVED", "version": original_version})
        assert conflict.status_code == 409
        resolved = client.post(f"/api/v1/recommendations/{recommendation_id}/status", headers=AUTHOR, json={"status": "RESOLVED", "version": original_version + 1})
        assert resolved.status_code == 200 and resolved.json()["status"] == "RESOLVED"
        reopened = client.post(f"/api/v1/recommendations/{recommendation_id}/status", headers=AUTHOR, json={"status": "UNDER_REVIEW", "version": original_version + 2})
        assert reopened.status_code == 200 and reopened.json()["status"] == "UNDER_REVIEW"
        created = client.post(f"/api/v1/recommendations/{recommendation_id}/review-case", headers=AUTHOR)
        assert created.status_code == 201
        case_id = created.json()["case_id"]
    finally:
        if case_id:
            _cleanup_case(case_id)
        with create_session_factory(get_settings().database_url)() as db:
            db.execute(delete(RecommendationEvent).where(RecommendationEvent.recommendation_id == recommendation_id, RecommendationEvent.actor == "phase12-test-author"))
            row = db.get(Recommendation, recommendation_id)
            if row:
                row.status, row.version, row.updated_at = original_status, original_version, row.generated_at
            db.commit()
