from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.intelligence.engine import RISK_MAXIMUM, duplicate_candidates, extract_features, risk_band
from app.main import app
from app.models import AnalyticalAlert, AnalyticsRun, DuplicateCandidate, MonitoringSignal, RiskAssessment
from app.db.session import create_session_factory
from app.core.config import get_settings

client = TestClient(app)
ADMIN = {"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR"}


def session():
    return create_session_factory(get_settings().database_url)()


def test_real_active_features_duplicate_candidates_and_assessments_are_database_backed():
    with session() as db:
        _, features = extract_features(db)
        assert features and all(item.work_key and item.house for item in features)
        # Use actual active-release descriptions while retaining a bounded test run.
        candidates = duplicate_candidates(features[:250], "test-release")
        assert all(item["work_a_key"] != item["work_b_key"] for item in candidates)
        assert all(item["work_a_key"] < item["work_b_key"] for item in candidates)
        assert db.scalar(select(func.count()).select_from(RiskAssessment)) == len(features)


def test_risk_formula_bands_and_alert_fingerprints_are_explainable_and_idempotent():
    assert risk_band(0) == "LOW" and risk_band(30) == "MEDIUM" and risk_band(60) == "HIGH" and risk_band(80) == "VERY_HIGH"
    with session() as db:
        alerts = db.scalars(select(AnalyticalAlert)).all()
        assert len({alert.fingerprint for alert in alerts}) == len(alerts)
        assessment = db.scalar(select(RiskAssessment).where(RiskAssessment.raw_score > 0))
        assert assessment is not None
        assert assessment.normalized_score == assessment.raw_score / RISK_MAXIMUM * 100
        assert db.scalar(select(func.count()).select_from(AnalyticsRun).where(AnalyticsRun.status == "COMPLETED")) >= 1


def test_protected_intelligence_api_requires_role_and_keeps_public_api_unchanged():
    assert client.get("/api/v1/dashboard/summary").status_code == 200
    assert client.get("/api/v1/risk/summary").status_code == 401
    summary = client.get("/api/v1/risk/summary", headers=ADMIN)
    assert summary.status_code == 200
    assert summary.json()["provenance"]["dataset_version"]
    works = client.get("/api/v1/risk/works", headers=ADMIN)
    assert works.status_code == 200 and works.json()
    work = works.json()[0]
    assert client.get(f"/api/v1/risk/works/{work['work_key']}", headers=ADMIN).status_code == 200
    assert client.get("/api/v1/alerts/summary", headers=ADMIN).status_code == 200
    assert client.get("/api/v1/duplicates/candidates", headers=ADMIN).status_code == 200
    assert client.get("/api/v1/anomalies/summary", headers=ADMIN).status_code == 200


def test_monitoring_frontend_contracts_are_paginated_scoped_and_database_backed():
    preflight = client.options("/api/v1/risk/summary", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "X-MPLADS-Role"})
    assert preflight.status_code == 200
    assert "x-mplads-role" in preflight.headers["access-control-allow-headers"].lower()

    paged_risk = client.get("/api/v1/risk/works?page=1&page_size=2&risk_band=HIGH", headers=ADMIN)
    assert paged_risk.status_code == 200
    assert paged_risk.json()["pagination"]["page_size"] == 2

    paged_alerts = client.get("/api/v1/alerts?page=1&page_size=2&severity=HIGH", headers=ADMIN)
    assert paged_alerts.status_code == 200
    assert all("state_name" in item and "district_or_ida" in item for item in paged_alerts.json()["items"])

    paged_duplicates = client.get("/api/v1/duplicates/candidates?page=1&page_size=2&similarity_min=0.8", headers=ADMIN)
    assert paged_duplicates.status_code == 200
    assert "pagination" in paged_duplicates.json()

    financial = client.get("/api/v1/monitoring/financial", headers=ADMIN)
    assert financial.status_code == 200
    assert "PAYMENT" in financial.json()["related_category_counts"]
    assert "financial_patterns" in financial.json()

    lifecycle = client.get("/api/v1/monitoring/lifecycle", headers=ADMIN)
    assert lifecycle.status_code == 200
    assert "recommendation_to_sanction" in lifecycle.json()["observed_lifecycle"]

    assert client.get("/api/v1/risk/works?page=1").status_code == 401
    assert client.get("/api/v1/risk/works?page=1", headers={"X-MPLADS-Role": "STATE_NODAL_AUTHORITY"}).status_code == 403
