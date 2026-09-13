"""Phase 15.2 Ask AI planning, entity, tool, and visualization coverage."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.ai.entities import resolve_question_entities
from app.ai.gemini_provider import GeminiConfigurationError
from app.ai.planner import Intent, ResultView, plan_question
from app.ai.registry import validate_tool_arguments
from app.ai.tools import execute_tool
from app.analytics.visualization_service import visualization_from_verified_tool
from app.api.deps import IntelligencePrincipal
from app.core.config import get_settings
from app.db.session import create_session_factory
from app.main import app
from app.models import RiskAssessment
from app.services.versioning_service import resolve_active_scope


client = TestClient(app)


@pytest.mark.parametrize(
    ("question", "intent", "tool_name", "view"),
    (
        ("How many monitored works are in the current active dataset?", Intent.DASHBOARD_QUERY, "get_dashboard_summary", None),
        ("Which House has higher recorded expenditure?", Intent.FINANCIAL_QUERY, "get_financial_by_house", None),
        ("Show expenditure by House.", Intent.FINANCIAL_QUERY, "get_financial_by_house", None),
        ("Show work status by House.", Intent.WORK_QUERY, "get_work_summary", ResultView.WORK_STATUS_BY_HOUSE),
        ("Show works by State.", Intent.WORK_QUERY, "get_work_summary", ResultView.WORKS_BY_STATE),
        ("Show expenditure by State.", Intent.FINANCIAL_QUERY, "get_financial_by_state", None),
        ("Show expenditure for Telangana.", Intent.FINANCIAL_QUERY, "get_financial_summary", ResultView.FINANCIAL_SUMMARY),
        ("How many works are in Telangana?", Intent.WORK_QUERY, "get_work_summary", ResultView.SUMMARY),
        ("Show completed works in Telangana.", Intent.LIFECYCLE_QUERY, "get_lifecycle_summary", None),
        ("Show sanction-to-completion duration distribution.", Intent.LIFECYCLE_QUERY, "get_work_summary", ResultView.LIFECYCLE_DURATION_DISTRIBUTION),
        ("Compare sanctioned and completed works by House.", Intent.WORK_QUERY, "get_work_summary", ResultView.SANCTIONED_COMPLETED_BY_HOUSE),
        ("Show risk distribution.", Intent.RISK_QUERY, "get_risk_summary", None),
        ("How many alerts are there?", Intent.ALERT_QUERY, "get_alert_summary", None),
        ("How many potential duplicate candidates are there?", Intent.DUPLICATE_QUERY, "get_duplicate_summary", None),
        ("What is the review backlog?", Intent.REVIEW_QUERY, "get_review_summary", None),
        ("How does this MP compare with peers?", Intent.BENCHMARK_QUERY, "get_benchmark_result", None),
    ),
)
def test_required_mplads_questions_plan_to_allowlisted_tools(question, intent, tool_name, view) -> None:
    plan, warning = plan_question(question)
    assert warning is None
    assert plan.intent == intent
    assert plan.tool_name == tool_name
    assert plan.result_view == view


@pytest.mark.parametrize("question", ("show work status by house", "SHOW WORK STATUS BY HOUSE", "Show Work Status By House"))
def test_status_by_house_capitalization_variants_use_one_plan(question: str) -> None:
    plan, warning = plan_question(question)
    assert warning is None
    assert plan.tool_name == "get_work_summary"
    assert plan.result_view == ResultView.WORK_STATUS_BY_HOUSE


@pytest.mark.parametrize(
    ("question", "tool_name"),
    (
        ("How many recommended works are there?", "get_work_summary"),
        ("How much has been allocated?", "get_financial_summary"),
        ("How much has been sanctioned?", "get_financial_summary"),
        ("Compare allocation and expenditure.", "get_financial_summary"),
        ("What is the completion ratio?", "get_work_summary"),
        ("Show work lifecycle by House.", "get_work_summary"),
        ("What are the main monitoring signals?", "get_executive_summary"),
        ("How many recommendations are under review?", "get_recommendations"),
        ("What is the current attention level?", "get_executive_summary"),
    ),
)
def test_additional_supported_categories_remain_allowlisted(question: str, tool_name: str) -> None:
    plan, warning = plan_question(question)
    assert warning is None
    assert plan.tool_name == tool_name


def test_forecasts_remain_unsupported() -> None:
    plan, warning = plan_question("What will MPLADS expenditure be next year?")
    assert plan.intent == Intent.UNSUPPORTED_QUERY
    assert plan.tool_name is None
    assert warning and "Forecasts" in warning


def test_underspecified_valid_questions_request_clarification() -> None:
    plan, warning = plan_question("Show expenditure")
    assert warning is None
    assert plan.clarification_required is True
    assert "by House" in (plan.clarification_message or "")


def test_entity_resolution_is_case_and_whitespace_normalized() -> None:
    with create_session_factory(get_settings().database_url)() as session:
        scope = resolve_active_scope(session)
        state = session.scalar(select(RiskAssessment.state_name).where(RiskAssessment.dataset_version == scope.release_version, RiskAssessment.state_name.is_not(None)).limit(1))
        assert state
        principal = IntelligencePrincipal(role="PLATFORM_ADMINISTRATOR", actor="phase152-entity")
        resolution = resolve_question_entities(f"How many works are in   {state.upper()}?", session, principal, scope.release_version)
    assert resolution.status == "RESOLVED"
    assert resolution.filters["state"] == state


def test_work_tools_execute_verified_active_release_aggregates() -> None:
    with create_session_factory(get_settings().database_url)() as session:
        scope = resolve_active_scope(session)
        principal = IntelligencePrincipal(role="PLATFORM_ADMINISTRATOR", actor="phase152-tool")
        status = execute_tool(
            "get_work_summary",
            validate_tool_arguments("get_work_summary", {"view": "WORK_STATUS_BY_HOUSE", "limit": 10}),
            session,
            principal,
            scope,
        )
        progress = execute_tool(
            "get_work_summary",
            validate_tool_arguments("get_work_summary", {"view": "SANCTIONED_COMPLETED_BY_HOUSE", "limit": 10}),
            session,
            principal,
            scope,
        )
        status_distribution = execute_tool(
            "get_work_summary",
            validate_tool_arguments("get_work_summary", {"view": "WORK_STATUS_DISTRIBUTION", "limit": 10}),
            session,
            principal,
            scope,
        )
        lifecycle_distribution = execute_tool(
            "get_work_summary",
            validate_tool_arguments("get_work_summary", {"view": "LIFECYCLE_DURATION_DISTRIBUTION", "limit": 10}),
            session,
            principal,
            scope,
        )
        duplicates = execute_tool(
            "get_duplicate_summary",
            validate_tool_arguments("get_duplicate_summary", {"limit": 10}),
            session,
            principal,
            scope,
        )
    assert status.success and "work_status_by_house" in status.data
    assert progress.success and "sanctioned_completed_by_house" in progress.data
    assert status_distribution.success and "work_status_distribution" in status_distribution.data
    assert "sanction_to_completion_duration_distribution" in lifecycle_distribution.data
    assert "potential_duplicate_candidates" in duplicates.data
    assert status.dataset_version == progress.dataset_version


def test_duplicate_count_visualization_uses_only_the_verified_tool_value() -> None:
    visualization = visualization_from_verified_tool("get_duplicate_summary", {"potential_duplicate_candidates": 3})
    assert visualization is not None
    assert visualization["chart_type"] == "KPI"
    assert visualization["rows"] == [{"label": "Potential Duplicate Candidates", "value": 3}]
    assert visualization["selection"]["source"] == "verified_tool_result"


def test_ask_ai_status_question_returns_a_verified_visual_and_never_needs_provider() -> None:
    headers = {"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "phase152-status-visual"}
    with patch("app.ai.assistant.generate_text", side_effect=GeminiConfigurationError("not configured")) as provider:
        response = client.post("/api/v1/ai/ask", headers=headers, json={"question": "Show work status by House."})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "WORK_QUERY"
    assert data["provenance"]["tool_used"] == "get_work_summary"
    assert "work_status_by_house" in data["tool_results_summary"]
    assert data["visualization"]["chart_type"] == "STACKED_BAR"
    assert data["visualization"]["selection"]["source"] == "verified_tool_result"
    assert data["dataset_version"] == data["tool_result"]["dataset_version"]
    provider.assert_called_once()


def test_ask_ai_forecast_is_rejected_before_provider() -> None:
    headers = {"X-MPLADS-Role": "PLATFORM_ADMINISTRATOR", "X-MPLADS-Actor": "phase152-forecast"}
    with patch("app.ai.assistant.generate_text") as provider:
        response = client.post("/api/v1/ai/ask", headers=headers, json={"question": "What will MPLADS expenditure be next year?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "UNSUPPORTED_QUERY"
    assert data["provenance"]["tool_used"] is None
    provider.assert_not_called()
