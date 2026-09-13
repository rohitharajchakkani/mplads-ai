"""Controlled natural-language planning for read-only, grounded Ask AI tools."""
from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.registry import get_tool, validate_tool_arguments


class Intent(str, Enum):
    DASHBOARD_QUERY = "DASHBOARD_QUERY"
    WORK_QUERY = "WORK_QUERY"
    FINANCIAL_QUERY = "FINANCIAL_QUERY"
    RISK_QUERY = "RISK_QUERY"
    ALERT_QUERY = "ALERT_QUERY"
    RECOMMENDATION_QUERY = "RECOMMENDATION_QUERY"
    REVIEW_QUERY = "REVIEW_QUERY"
    BENCHMARK_QUERY = "BENCHMARK_QUERY"
    EXECUTIVE_QUERY = "EXECUTIVE_QUERY"
    LIFECYCLE_QUERY = "LIFECYCLE_QUERY"
    DUPLICATE_QUERY = "DUPLICATE_QUERY"
    MONITORING_SIGNAL_QUERY = "MONITORING_SIGNAL_QUERY"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"


class SortDirection(str, Enum):
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class GroupBy(str, Enum):
    STATE = "STATE"
    HOUSE = "HOUSE"
    RISK_BAND = "RISK_BAND"
    SEVERITY = "SEVERITY"
    STATUS = "STATUS"


class Metric(str, Enum):
    MONITORED_WORKS = "MONITORED_WORKS"
    WORKS = "WORKS"
    RECOMMENDED_WORKS = "RECOMMENDED_WORKS"
    SANCTIONED_WORKS = "SANCTIONED_WORKS"
    COMPLETED_WORKS = "COMPLETED_WORKS"
    WORK_STATUS = "WORK_STATUS"
    COMPLETION_RATIO = "COMPLETION_RATIO"
    EXPENDITURE = "EXPENDITURE"
    ALLOCATION = "ALLOCATION"
    SANCTION_AMOUNT = "SANCTION_AMOUNT"
    RISK_DISTRIBUTION = "RISK_DISTRIBUTION"
    ALERT_DISTRIBUTION = "ALERT_DISTRIBUTION"
    REVIEW_BACKLOG = "REVIEW_BACKLOG"
    MONITORING_SIGNALS = "MONITORING_SIGNALS"
    POTENTIAL_DUPLICATES = "POTENTIAL_DUPLICATES"


class ResultView(str, Enum):
    SUMMARY = "SUMMARY"
    WORKS_BY_HOUSE = "WORKS_BY_HOUSE"
    WORKS_BY_STATE = "WORKS_BY_STATE"
    WORK_STATUS_BY_HOUSE = "WORK_STATUS_BY_HOUSE"
    WORK_STATUS_BY_STATE = "WORK_STATUS_BY_STATE"
    WORK_STATUS_DISTRIBUTION = "WORK_STATUS_DISTRIBUTION"
    SANCTIONED_COMPLETED_BY_HOUSE = "SANCTIONED_COMPLETED_BY_HOUSE"
    SANCTIONED_COMPLETED_BY_STATE = "SANCTIONED_COMPLETED_BY_STATE"
    COMPLETION_RATIO = "COMPLETION_RATIO"
    LIFECYCLE_DURATION_DISTRIBUTION = "LIFECYCLE_DURATION_DISTRIBUTION"
    FINANCIAL_SUMMARY = "FINANCIAL_SUMMARY"
    SANCTIONED_AMOUNT_BY_HOUSE = "SANCTIONED_AMOUNT_BY_HOUSE"
    ALLOCATION_BY_HOUSE = "ALLOCATION_BY_HOUSE"
    ALLOCATION_VS_EXPENDITURE_BY_HOUSE = "ALLOCATION_VS_EXPENDITURE_BY_HOUSE"


_NAVIGATION_TARGETS = frozenset({
    "/works", "/monitoring/risk", "/monitoring/alerts", "/monitoring/financial",
    "/monitoring/lifecycle", "/monitoring/reviews", "/monitoring/benchmarking",
    "/monitoring/recommendations", "/monitoring/executive", "/monitoring/duplicates",
})
_GROUPS_BY_TOOL = {
    "get_financial_by_state": {GroupBy.STATE},
    "get_financial_by_house": {GroupBy.HOUSE},
    "get_work_summary": {GroupBy.HOUSE, GroupBy.STATE, GroupBy.STATUS},
    "get_financial_summary": {GroupBy.HOUSE},
    "get_risk_summary": {GroupBy.RISK_BAND},
    "get_alert_summary": {GroupBy.SEVERITY},
    "get_recommendations": {GroupBy.STATUS},
    "get_review_summary": {GroupBy.STATUS},
}
_VIEWS_BY_TOOL = {
    "get_work_summary": {
        ResultView.SUMMARY, ResultView.WORKS_BY_HOUSE, ResultView.WORKS_BY_STATE,
        ResultView.WORK_STATUS_BY_HOUSE, ResultView.WORK_STATUS_BY_STATE,
        ResultView.WORK_STATUS_DISTRIBUTION,
        ResultView.SANCTIONED_COMPLETED_BY_HOUSE, ResultView.SANCTIONED_COMPLETED_BY_STATE,
        ResultView.COMPLETION_RATIO, ResultView.LIFECYCLE_DURATION_DISTRIBUTION,
    },
    "get_financial_summary": {
        ResultView.FINANCIAL_SUMMARY, ResultView.SANCTIONED_AMOUNT_BY_HOUSE,
        ResultView.ALLOCATION_BY_HOUSE, ResultView.ALLOCATION_VS_EXPENDITURE_BY_HOUSE,
    },
}


class AiQueryPlan(BaseModel):
    """A strict, non-SQL plan. Gemini neither produces nor edits this model."""
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    tool_name: str | None = None
    metric: Metric | None = None
    group_by: GroupBy | None = None
    filters: dict[str, str | int | None] = Field(default_factory=dict)
    result_view: ResultView | None = None
    sort: SortDirection | None = None
    limit: int = Field(default=10, ge=1, le=25)
    entity_type: str | None = None
    entity_id: str | None = Field(default=None, max_length=110)
    navigation_target: str | None = None
    clarification_required: bool = False
    clarification_message: str | None = None
    clarification_options: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def validate_plan(self):
        if self.intent == Intent.UNSUPPORTED_QUERY:
            if self.tool_name is not None:
                raise ValueError("Unsupported intents cannot select tools.")
            return self
        if not self.tool_name:
            raise ValueError("Supported intents require an allowlisted tool.")
        tool = get_tool(self.tool_name)
        arguments = {**self.filters, "limit": self.limit}
        if self.result_view:
            arguments["view"] = self.result_view.value
        validate_tool_arguments(self.tool_name, arguments)
        if self.group_by and self.group_by not in _GROUPS_BY_TOOL.get(self.tool_name, set()):
            raise ValueError("Unsupported grouping for this AI tool.")
        if self.result_view and self.result_view not in _VIEWS_BY_TOOL.get(self.tool_name, set()):
            raise ValueError("Unsupported result view for this AI tool.")
        if self.sort and self.tool_name != "get_financial_by_state":
            raise ValueError("Unsupported sort for this AI tool.")
        if self.entity_type and self.entity_type not in tool.supported_entity_types:
            raise ValueError("Unsupported entity type.")
        if self.navigation_target and self.navigation_target not in _NAVIGATION_TARGETS:
            raise ValueError("Unsupported navigation target.")
        return self


_BLOCKED_REQUEST_FRAGMENTS = (
    "ignore previous", "system prompt", "database credential", "database password", "api key",
    "run sql", "raw sql", "read the raw", "raw csv", "raw excel", "filesystem",
    "act as ministry", "bypass scope", "disable authorization", "disable auth",
    "create review", "update review", "delete review", "change dataset", "send notification",
)
_FORECAST_FRAGMENTS = ("forecast", "predict", "physical progress", "next year", "next financial year", "next fiscal year")


def _normalize_question(question: str) -> str:
    """Normalize ordinary wording differences without interpreting new facts."""
    return " ".join(re.sub(r"[^\w]+", " ", question.casefold()).replace("_", " ").split())


def _has(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _house_filter(text: str) -> dict[str, str]:
    if _has(text, "lok sabha", "loksabha"):
        return {"house": "LOK_SABHA"}
    if _has(text, "rajya sabha", "rajyasabha"):
        return {"house": "RAJYA_SABHA"}
    return {}


def _group(text: str) -> GroupBy | None:
    if _has(text, "by house", "for each house", "between houses", "across houses"):
        return GroupBy.HOUSE
    if _has(text, "by state", "by states", "for each state", "across states", "across state"):
        return GroupBy.STATE
    if _has(text, "by status", "by work status", "status distribution"):
        return GroupBy.STATUS
    if _has(text, "by severity", "severity distribution"):
        return GroupBy.SEVERITY
    return None


def _clarification(intent: Intent, tool_name: str, metric: Metric, message: str, options: list[str], target: str) -> tuple[AiQueryPlan, None]:
    return AiQueryPlan(
        intent=intent,
        tool_name=tool_name,
        metric=metric,
        limit=10,
        navigation_target=target,
        clarification_required=True,
        clarification_message=message,
        clarification_options=options,
    ), None


def plan_question(question: str) -> tuple[AiQueryPlan, str | None]:
    """Map broad MPLADS wording to fixed read-only tools and bounded result views."""
    text = _normalize_question(question)
    if any(fragment in text for fragment in _BLOCKED_REQUEST_FRAGMENTS):
        return AiQueryPlan(intent=Intent.UNSUPPORTED_QUERY), "This request is not supported. Ask AI is read-only and cannot reveal secrets, access files, run SQL, or change authorization."
    if any(fragment in text for fragment in _FORECAST_FRAGMENTS):
        return AiQueryPlan(intent=Intent.UNSUPPORTED_QUERY), "Forecasts, predictions, and unsupported source metrics are not available from the current active dataset."

    filters = _house_filter(text)
    group_by = _group(text)
    has_work = _has(text, "work", "works", "monitored")
    has_finance = _has(text, "expenditure", "spend", "spent", "financial", "disbursed", "allocation", "allocated", "sanction amount", "sanctioned amount") or ("sanctioned" in text and not has_work)

    # Protected monitoring, review, and executive questions take precedence over
    # generic words such as "status" or "works".
    if _has(text, "benchmark", "peer"):
        return AiQueryPlan(intent=Intent.BENCHMARK_QUERY, tool_name="get_benchmark_result", limit=10, navigation_target="/monitoring/benchmarking", filters=filters), None
    if _has(text, "recommendation"):
        return AiQueryPlan(intent=Intent.RECOMMENDATION_QUERY, tool_name="get_recommendations", group_by=GroupBy.STATUS, limit=10, navigation_target="/monitoring/recommendations", filters=filters), None
    if _has(text, "review", "case", "follow up", "followup", "backlog"):
        return AiQueryPlan(intent=Intent.REVIEW_QUERY, tool_name="get_review_summary", metric=Metric.REVIEW_BACKLOG, group_by=GroupBy.STATUS, limit=10, navigation_target="/monitoring/reviews", filters=filters), None
    if _has(text, "alert", "alerts"):
        return AiQueryPlan(intent=Intent.ALERT_QUERY, tool_name="get_alert_summary", metric=Metric.ALERT_DISTRIBUTION, group_by=GroupBy.SEVERITY, limit=10, navigation_target="/monitoring/alerts", filters=filters), None
    if _has(text, "risk", "high risk", "monitoring priority"):
        return AiQueryPlan(intent=Intent.RISK_QUERY, tool_name="get_risk_summary", metric=Metric.RISK_DISTRIBUTION, group_by=GroupBy.RISK_BAND, limit=10, navigation_target="/monitoring/risk", filters=filters), None
    if _has(text, "potential duplicate", "duplicate candidate", "duplicate candidates"):
        return AiQueryPlan(intent=Intent.DUPLICATE_QUERY, tool_name="get_duplicate_summary", metric=Metric.POTENTIAL_DUPLICATES, limit=10, navigation_target="/monitoring/duplicates"), None
    if _has(text, "attention level", "drivers of attention", "monitoring overview", "executive", "main monitoring signals"):
        return AiQueryPlan(intent=Intent.EXECUTIVE_QUERY, tool_name="get_executive_summary", metric=Metric.MONITORED_WORKS, limit=10, navigation_target="/monitoring/executive", filters=filters), None
    if _has(text, "monitoring signal", "signals for this work"):
        return AiQueryPlan(intent=Intent.MONITORING_SIGNAL_QUERY, tool_name="get_monitoring_signal_detail", metric=Metric.MONITORING_SIGNALS, limit=10, navigation_target="/monitoring/risk", filters=filters), None
    if _has(text, "monitored works", "monitored work") and _has(text, "how many", "number of", "total", "current active dataset"):
        return AiQueryPlan(intent=Intent.DASHBOARD_QUERY, tool_name="get_dashboard_summary", metric=Metric.MONITORED_WORKS, limit=10, navigation_target="/works", filters=filters), None

    if has_finance:
        if _has(text, "allocation") and _has(text, "expenditure", "compare"):
            return AiQueryPlan(intent=Intent.FINANCIAL_QUERY, tool_name="get_financial_summary", metric=Metric.ALLOCATION, group_by=GroupBy.HOUSE, result_view=ResultView.ALLOCATION_VS_EXPENDITURE_BY_HOUSE, limit=10, navigation_target="/monitoring/financial", filters=filters), None
        if _has(text, "allocation", "allocated"):
            view = ResultView.ALLOCATION_BY_HOUSE if group_by == GroupBy.HOUSE or _has(text, "by house") else ResultView.FINANCIAL_SUMMARY
            return AiQueryPlan(intent=Intent.FINANCIAL_QUERY, tool_name="get_financial_summary", metric=Metric.ALLOCATION, group_by=GroupBy.HOUSE if view == ResultView.ALLOCATION_BY_HOUSE else None, result_view=view, limit=10, navigation_target="/monitoring/financial", filters=filters), None
        if _has(text, "sanction amount", "sanctioned amount", "how much has been sanctioned"):
            view = ResultView.SANCTIONED_AMOUNT_BY_HOUSE if group_by == GroupBy.HOUSE or _has(text, "by house") else ResultView.FINANCIAL_SUMMARY
            return AiQueryPlan(intent=Intent.FINANCIAL_QUERY, tool_name="get_financial_summary", metric=Metric.SANCTION_AMOUNT, group_by=GroupBy.HOUSE if view == ResultView.SANCTIONED_AMOUNT_BY_HOUSE else None, result_view=view, limit=10, navigation_target="/monitoring/financial", filters=filters), None
        if group_by == GroupBy.HOUSE or "house" in text or filters.get("house"):
            return AiQueryPlan(intent=Intent.FINANCIAL_QUERY, tool_name="get_financial_by_house", metric=Metric.EXPENDITURE, group_by=GroupBy.HOUSE, limit=10, navigation_target="/monitoring/financial", filters=filters), None
        if group_by == GroupBy.STATE or _has(text, "highest expenditure", "top expenditure", "which states"):
            return AiQueryPlan(intent=Intent.FINANCIAL_QUERY, tool_name="get_financial_by_state", metric=Metric.EXPENDITURE, group_by=GroupBy.STATE, limit=10, navigation_target="/monitoring/financial", filters=filters), None
        if _has(text, "total", "how much", "what is"):
            return AiQueryPlan(intent=Intent.FINANCIAL_QUERY, tool_name="get_financial_summary", metric=Metric.EXPENDITURE, result_view=ResultView.FINANCIAL_SUMMARY, limit=10, navigation_target="/monitoring/financial", filters=filters), None
        if "national" in text:
            return AiQueryPlan(intent=Intent.FINANCIAL_QUERY, tool_name="get_financial_by_state", metric=Metric.EXPENDITURE, group_by=GroupBy.STATE, limit=10, navigation_target="/monitoring/financial", filters=filters), None
        if re.search(r"\b(?:for|in|within)\b", text):
            return AiQueryPlan(intent=Intent.FINANCIAL_QUERY, tool_name="get_financial_summary", metric=Metric.EXPENDITURE, result_view=ResultView.FINANCIAL_SUMMARY, limit=10, navigation_target="/monitoring/financial", filters=filters), None
        return _clarification(Intent.FINANCIAL_QUERY, "get_financial_summary", Metric.EXPENDITURE, "Would you like total expenditure, expenditure by House, or expenditure by State?", ["Total expenditure", "Expenditure by House", "Expenditure by State"], "/monitoring/financial")

    if _has(text, "completion ratio"):
        return AiQueryPlan(intent=Intent.LIFECYCLE_QUERY, tool_name="get_work_summary", metric=Metric.COMPLETION_RATIO, result_view=ResultView.COMPLETION_RATIO, limit=10, navigation_target="/monitoring/lifecycle", filters=filters), None
    if _has(text, "work lifecycle", "lifecycle by"):
        view = ResultView.SANCTIONED_COMPLETED_BY_STATE if group_by == GroupBy.STATE else ResultView.SANCTIONED_COMPLETED_BY_HOUSE
        return AiQueryPlan(intent=Intent.LIFECYCLE_QUERY, tool_name="get_work_summary", metric=Metric.COMPLETED_WORKS, group_by=group_by or GroupBy.HOUSE, result_view=view, limit=10, navigation_target="/monitoring/lifecycle", filters=filters), None
    if _has(text, "sanction to completion", "duration distribution", "lifecycle duration"):
        return AiQueryPlan(intent=Intent.LIFECYCLE_QUERY, tool_name="get_work_summary", metric=Metric.COMPLETED_WORKS, result_view=ResultView.LIFECYCLE_DURATION_DISTRIBUTION, limit=10, navigation_target="/monitoring/lifecycle", filters=filters), None
    if _has(text, "work status", "status of works", "status for works"):
        view = ResultView.WORK_STATUS_BY_STATE if group_by == GroupBy.STATE else ResultView.WORK_STATUS_BY_HOUSE if group_by == GroupBy.HOUSE else ResultView.WORK_STATUS_DISTRIBUTION
        return AiQueryPlan(intent=Intent.WORK_QUERY, tool_name="get_work_summary", metric=Metric.WORK_STATUS, group_by=group_by, result_view=view, limit=10, navigation_target="/works", filters=filters), None
    has_sanctioned = _has(text, "sanctioned")
    has_completed = _has(text, "completed")
    if (has_sanctioned or has_completed) and has_work:
        if has_sanctioned and has_completed:
            view = ResultView.SANCTIONED_COMPLETED_BY_STATE if group_by == GroupBy.STATE else ResultView.SANCTIONED_COMPLETED_BY_HOUSE
            return AiQueryPlan(intent=Intent.WORK_QUERY, tool_name="get_work_summary", metric=Metric.SANCTIONED_WORKS, group_by=group_by or GroupBy.HOUSE, result_view=view, limit=10, navigation_target="/works", filters=filters), None
        if has_completed:
            return AiQueryPlan(intent=Intent.LIFECYCLE_QUERY, tool_name="get_lifecycle_summary", metric=Metric.COMPLETED_WORKS, limit=10, navigation_target="/works", filters=filters), None
        return AiQueryPlan(intent=Intent.WORK_QUERY, tool_name="get_work_summary", metric=Metric.SANCTIONED_WORKS, result_view=ResultView.SUMMARY, limit=10, navigation_target="/works", filters=filters), None
    if has_work:
        if group_by == GroupBy.HOUSE:
            return AiQueryPlan(intent=Intent.WORK_QUERY, tool_name="get_work_summary", metric=Metric.WORKS, group_by=GroupBy.HOUSE, result_view=ResultView.WORKS_BY_HOUSE, limit=10, navigation_target="/works", filters=filters), None
        if group_by == GroupBy.STATE:
            return AiQueryPlan(intent=Intent.WORK_QUERY, tool_name="get_work_summary", metric=Metric.WORKS, group_by=GroupBy.STATE, result_view=ResultView.WORKS_BY_STATE, limit=10, navigation_target="/works", filters=filters), None
        if _has(text, "how many", "number of", "total", "current active dataset", "in "):
            return AiQueryPlan(intent=Intent.WORK_QUERY, tool_name="get_work_summary", metric=Metric.WORKS, result_view=ResultView.SUMMARY, limit=10, navigation_target="/works", filters=filters), None
        return _clarification(Intent.WORK_QUERY, "get_work_summary", Metric.WORKS, "Would you like the total number of works, works by House, or works by State?", ["Total works", "Works by House", "Works by State"], "/works")

    return AiQueryPlan(intent=Intent.UNSUPPORTED_QUERY), "I can answer supported MPLADS questions about works, expenditure, allocation, lifecycle, risk, alerts, reviews, benchmarks, recommendations, and executive intelligence."
