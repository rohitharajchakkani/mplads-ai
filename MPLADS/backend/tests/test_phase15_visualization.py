"""Phase 15 public filter and visualization contracts against an isolated DB copy."""
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.analytics.visualization_service import visualization_from_verified_tool
from app.db.session import create_session_factory
from app.main import app
from app.models import CanonicalWork, DatasetVersion
from app.services.versioning_service import resolve_active_scope


client = TestClient(app)


def _sample() -> tuple[str, str, str, str, str]:
    with create_session_factory(get_settings().database_url)() as session:
        scope = resolve_active_scope(session)
        row = session.execute(
            select(
                CanonicalWork.house,
                CanonicalWork.state_name,
                CanonicalWork.district_or_ida,
                CanonicalWork.mp_source_name,
                CanonicalWork.normalized_work_id,
            )
            .join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id)
            .where(
                DatasetVersion.batch_id == scope.batch_id,
                CanonicalWork.state_name.is_not(None),
                CanonicalWork.district_or_ida.is_not(None),
                CanonicalWork.mp_source_name.is_not(None),
            )
            .limit(1)
        ).one()
        return tuple(str(value) for value in row)


def test_text_filters_are_case_and_whitespace_insensitive() -> None:
    house, state, district, mp, _ = _sample()
    expected = client.get(
        "/api/v1/dashboard/summary",
        params={"house": house, "state": state, "district_or_ida": district, "mp": mp},
    )
    normalized = client.get(
        "/api/v1/dashboard/summary",
        params={
            "house": house.lower().replace("_", " "),
            "state": f"  {state.lower().replace(' ', '   ')}  ",
            "district_or_ida": f"  {district.lower()}  ",
            "mp": f"  {mp.lower()}  ",
        },
    )
    assert expected.status_code == normalized.status_code == 200
    assert expected.json()["data"]["total_canonical_works"] == normalized.json()["data"]["total_canonical_works"]


def test_cascading_option_lists_are_active_release_backed() -> None:
    house, state, district, mp, work = _sample()
    state_options = client.get("/api/v1/filters/options", params={"field": "state", "house": house})
    district_options = client.get("/api/v1/filters/options", params={"field": "district_or_ida", "house": house, "state": state})
    mp_options = client.get("/api/v1/filters/options", params={"field": "mp", "house": house, "state": state, "district_or_ida": district})
    work_options = client.get("/api/v1/filters/options", params={"field": "work", "house": house, "state": state, "district_or_ida": district, "mp": mp})
    for response in (state_options, district_options, mp_options, work_options):
        assert response.status_code == 200
        assert response.json()["provenance"]["release_version"]
    assert state in {row["value"] for row in state_options.json()["data"]["options"]}
    assert district in {row["value"] for row in district_options.json()["data"]["options"]}
    assert mp in {row["value"] for row in mp_options.json()["data"]["options"]}
    assert work in {row["label"] for row in work_options.json()["data"]["options"]}


def test_visualization_specs_are_aggregated_and_never_fabricate_trends() -> None:
    grouped = client.get("/api/v1/visualizations/explore", params={"metric": "expenditure", "group_by": "state"})
    assert grouped.status_code == 200
    body = grouped.json()
    assert body["data"]["chart_type"] == "HORIZONTAL_BAR"
    assert body["data"]["unit"] == "Expenditure"
    assert body["data"]["record_count"] == len(body["data"]["rows"])
    assert body["data"]["selection"]["source"] == "active_release_aggregate"
    assert body["provenance"]["release_version"]

    unavailable = client.get("/api/v1/visualizations/explore", params={"metric": "works", "group_by": "period", "state": "not a source state"})
    assert unavailable.status_code == 200
    assert unavailable.json()["data"]["data_available"] is False
    assert unavailable.json()["data"]["message"] == "Trend unavailable for the selected data."


def test_extended_chart_selection_rules_are_explicit_and_active_release_backed() -> None:
    cases = (
        ("works", "house", "PIE", "small_category_share"),
        ("expenditure", "house", "DONUT", "categorical_share"),
        ("progress", "state", "GROUPED_BAR", "two_metric_category_comparison"),
        ("status", "house", "STACKED_BAR", "category_composition"),
        ("lifecycle", "distribution", "HISTOGRAM", "observed_numeric_distribution"),
        ("expenditure", "period", "AREA", "dated_amount_sequence"),
        ("relationship", "state", "SCATTER", "two_numeric_metrics"),
        ("works", "state_category", "HEATMAP", "category_matrix"),
    )
    for metric, group_by, expected_chart, expected_rule in cases:
        response = client.get("/api/v1/visualizations/explore", params={"metric": metric, "group_by": group_by})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["selection"]["rule"] == expected_rule
        assert data["selection"]["source"] == "active_release_aggregate"
        # A table fallback is valid only when the active release has no data for the requested form.
        assert data["chart_type"] == expected_chart or (data["chart_type"] == "TABLE" and data["data_available"] is False)
        assert data["record_count"] == len(data["rows"])


def test_invalid_visualization_dimensions_are_rejected() -> None:
    response = client.get("/api/v1/visualizations/explore", params={"metric": "expenditure", "group_by": "status"})
    assert response.status_code == 422


def test_ask_ai_visualization_is_derived_only_from_the_verified_tool_payload() -> None:
    payload = {"top_states_by_expenditure": [{"state": "Verified State", "expenditure": "123.45"}]}
    visualization = visualization_from_verified_tool("get_financial_by_state", payload)
    assert visualization is not None
    assert visualization["chart_type"] == "HORIZONTAL_BAR"
    assert visualization["rows"] == [{"label": "Verified State", "value": 123.45}]
    assert visualization["selection"]["source"] == "verified_tool_result"
    assert visualization_from_verified_tool("get_risk_summary", {}) is None
