import base64
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import distinct, func, select

from app.db.session import create_session_factory
from app.core.config import get_settings
from app.main import app
from app.models import CanonicalWork, DatasetRelease, DatasetVersion, ExpenditureTransaction, SanctionedWorkRecord
from app.services.versioning_service import resolve_active_scope

client = TestClient(app)


def db_session():
    return create_session_factory(get_settings().database_url)()


def encoded(*values: str) -> str:
    return base64.urlsafe_b64encode("\x1f".join(values).encode()).decode().rstrip("=")


def test_health_reports_live_database_release_and_security_headers() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database_status"] == "ok"
    assert body["active_dataset_status"] == "ACTIVE"
    assert body["migration_version"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_dashboard_summary_matches_independent_database_aggregations() -> None:
    with db_session() as db:
        scope = resolve_active_scope(db)
        expected_works = db.scalar(select(func.count(distinct(CanonicalWork.canonical_work_key))).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
        expected_expenditure = db.scalar(select(func.coalesce(func.sum(ExpenditureTransaction.disbursed_amount), 0)).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
        expected_sanction = db.scalar(select(func.coalesce(func.sum(SanctionedWorkRecord.sanction_amount), 0)).join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_canonical_works"] == expected_works
    assert data["total_expenditure"] == str(expected_expenditure)
    assert data["total_sanction_amount"] == str(expected_sanction)


def test_dashboard_filters_recalculate_from_matching_database_rows() -> None:
    with db_session() as db:
        scope = resolve_active_scope(db)
        sample = db.execute(select(CanonicalWork.house, CanonicalWork.state_name, CanonicalWork.district_or_ida, CanonicalWork.mp_source_name).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, CanonicalWork.state_name.is_not(None), CanonicalWork.district_or_ida.is_not(None), CanonicalWork.mp_source_name.is_not(None)).limit(1)).one()
        expected = db.scalar(select(func.count()).select_from(CanonicalWork).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, CanonicalWork.house == sample.house, CanonicalWork.state_name == sample.state_name, CanonicalWork.district_or_ida == sample.district_or_ida, CanonicalWork.mp_source_name == sample.mp_source_name))
    response = client.get("/api/v1/dashboard/summary", params={"house": sample.house, "state": sample.state_name, "district_or_ida": sample.district_or_ida, "mp": sample.mp_source_name})
    assert response.status_code == 200
    assert response.json()["data"]["total_canonical_works"] == expected


def test_unsupported_and_invalid_filters_return_truthful_errors() -> None:
    assert client.get("/api/v1/dashboard/summary", params={"house": "INVALID"}).status_code == 422
    assert client.get("/api/v1/dashboard/summary", params={"sector": "anything"}).status_code == 422
    sector = client.get("/api/v1/dashboard/sector-summary")
    assert sector.status_code == 200
    assert sector.json()["data"]["data_available"] is False


def test_mp_list_search_detail_and_not_found_are_database_backed() -> None:
    listing = client.get("/api/v1/mps", params={"page": 1, "page_size": 1})
    assert listing.status_code == 200
    item = listing.json()["items"][0]
    detail = client.get(f"/api/v1/mps/{item['mp_id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["name"] == item["name"]
    searched = client.get("/api/v1/mps", params={"search": item["name"], "page_size": 10})
    assert any(row["mp_id"] == item["mp_id"] for row in searched.json()["items"])
    assert client.get(f"/api/v1/mps/{encoded('LOK_SABHA', 'not-a-source-mp')}").status_code == 404


def test_state_and_district_lists_details_and_not_found_are_database_backed() -> None:
    state = client.get("/api/v1/states", params={"page_size": 1}).json()["items"][0]
    assert client.get(f"/api/v1/states/{state['state_id']}").status_code == 200
    district = client.get("/api/v1/districts", params={"page_size": 1}).json()["items"][0]
    assert client.get(f"/api/v1/districts/{district['district_id']}").status_code == 200
    assert client.get(f"/api/v1/states/{encoded('not-a-source-state')}").status_code == 404
    assert client.get(f"/api/v1/districts/{encoded('not-a-source-state', 'not-a-source-district')}").status_code == 404


def test_works_server_pagination_search_filters_and_detail() -> None:
    first = client.get("/api/v1/works", params={"page": 1, "page_size": 2})
    second = client.get("/api/v1/works", params={"page": 2, "page_size": 2})
    assert first.status_code == second.status_code == 200
    assert first.json()["pagination"]["total"] >= len(first.json()["items"])
    assert first.json()["items"] != second.json()["items"]
    work = first.json()["items"][0]
    detail = client.get(f"/api/v1/works/{work['canonical_work_key']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["work"]["canonical_work_key"] == work["canonical_work_key"]
    searched = client.get("/api/v1/works", params={"search": work["work_id"], "page_size": 10})
    assert any(row["canonical_work_key"] == work["canonical_work_key"] for row in searched.json()["items"])
    assert client.get("/api/v1/works/LOK_SABHA:NOT_A_SOURCE_WORK").status_code == 404


def test_financial_api_and_work_detail_expenditure_match_database() -> None:
    with db_session() as db:
        scope = resolve_active_scope(db)
        work = db.scalar(select(ExpenditureTransaction.canonical_work_key).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id).limit(1))
        expected_total = db.scalar(select(func.coalesce(func.sum(ExpenditureTransaction.disbursed_amount), 0)).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
        expected_work_total = db.scalar(select(func.coalesce(func.sum(ExpenditureTransaction.disbursed_amount), 0)).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, ExpenditureTransaction.canonical_work_key == work))
    assert client.get("/api/v1/financial/summary").json()["data"]["total_expenditure"] == str(expected_total)
    assert client.get("/api/v1/financial/by-house").status_code == 200
    assert client.get("/api/v1/financial/by-state").status_code == 200
    assert client.get("/api/v1/financial/by-mp").status_code == 200
    assert client.get("/api/v1/financial/by-district").status_code == 200
    assert client.get(f"/api/v1/works/{work}").json()["data"]["expenditure"]["total"] == str(expected_work_total)


def test_lifecycle_trends_search_quality_and_dataset_metadata_have_provenance() -> None:
    for path in ["/api/v1/trends/lifecycle", "/api/v1/trends/works", "/api/v1/trends/expenditure", "/api/v1/trends/completion", "/api/v1/data-quality/summary", "/api/v1/datasets/active", "/api/v1/datasets/versions"]:
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["provenance"]["release_version"]
    with db_session() as db:
        scope = resolve_active_scope(db)
        work_id = db.scalar(select(CanonicalWork.normalized_work_id).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id).limit(1))
    results = client.get("/api/v1/search", params={"q": work_id, "page_size": 10})
    assert results.status_code == 200
    assert any(item["entity_type"] == "WORK" for item in results.json()["items"])


def test_active_dataset_metadata_matches_database_release() -> None:
    with db_session() as db:
        release = db.scalar(select(DatasetRelease).where(DatasetRelease.status == "ACTIVE"))
    response = client.get("/api/v1/datasets/active")
    assert response.status_code == 200
    assert response.json()["data"]["release_version"] == release.release_version
