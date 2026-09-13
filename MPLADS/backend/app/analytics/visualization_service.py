"""Deterministic, database-backed chart specifications for the public explorer."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from math import ceil, sqrt
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.analytics.dashboard_service import core_metrics, house_comparison
from app.analytics.financial_analytics_service import expenditure_by
from app.analytics.geography_analytics_service import summarize_by
from app.analytics.lifecycle_analytics_service import lifecycle_summary
from app.analytics.query import active_works_statement
from app.analytics.trend_analytics_service import expenditure_trend, works_trend
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.analytics.work_analytics_service import status_distribution
from app.models import CanonicalWork, CompletedWorkRecord, DatasetVersion, SanctionedWorkRecord
from app.services.versioning_service import resolve_active_scope


_METRICS = {"works", "expenditure", "status", "lifecycle", "progress", "relationship"}
_GROUPS = {"summary", "house", "state", "district_or_ida", "mp", "work", "period", "status", "distribution", "state_category"}
_MAX_HEATMAP_STATES = 20
_MAX_HEATMAP_CATEGORIES = 12


def _number(value: Any) -> int | float:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return value
    return float(value or 0)


def _display(value: Any, *, house: bool = False) -> str:
    text = str(value) if value not in (None, "") else "Not available"
    return text.replace("_", " ") if house else text


def _selection(rule: str, rationale: str, *, source: str = "active_release_aggregate") -> dict[str, str]:
    """Explain the deterministic choice without implying a predictive model."""
    return {"rule": rule, "rationale": rationale, "source": source}


def _result(scope, filters: AnalyticsFilters, **data: Any) -> AnalyticsResult:
    data.setdefault("applied_filters", {key: value for key, value in filters.as_dict().items() if value is not None})
    data.setdefault("selection", _selection("table_fallback", "The selected result is represented as an accessible supporting table."))
    return AnalyticsResult(data, provenance("visualization_service.explore", scope, filters))


def _unavailable(scope, filters: AnalyticsFilters, title: str, message: str, *, rule: str = "unavailable") -> AnalyticsResult:
    return _result(
        scope,
        filters,
        title=title,
        description=message,
        chart_type="TABLE",
        x_axis=None,
        y_axis=None,
        unit=None,
        series=[],
        rows=[],
        record_count=0,
        data_available=False,
        message=message,
        selection=_selection(rule, message),
    )


def _category_spec(
    scope,
    filters: AnalyticsFilters,
    title: str,
    description: str,
    rows: list[dict],
    *,
    chart_type: str,
    unit: str,
    x_axis: str,
    y_axis: str,
    selection_rule: str = "categorical_comparison",
    selection_rationale: str = "One observed value is compared across categorical groups.",
) -> AnalyticsResult:
    if not rows:
        return _unavailable(scope, filters, title, "No records match the selected filters.", rule=selection_rule)
    return _result(
        scope,
        filters,
        title=title,
        description=description,
        chart_type=chart_type,
        x_axis=x_axis,
        y_axis=y_axis,
        unit=unit,
        series=[{"key": "value", "label": unit}],
        rows=rows,
        record_count=len(rows),
        data_available=True,
        selection=_selection(selection_rule, selection_rationale),
    )


def _works_by_work(session: Session, scope, filters: AnalyticsFilters) -> list[dict]:
    works = active_works_statement(scope, filters).subquery()
    rows = session.execute(
        select(works.c.normalized_work_id.label("label"), func.count().label("value"))
        .where(works.c.normalized_work_id.is_not(None))
        .group_by(works.c.normalized_work_id)
        .order_by(func.count().desc(), works.c.normalized_work_id.asc())
        .limit(100)
    ).all()
    return [{"label": row.label, "value": int(row.value)} for row in rows]


def _progress_by_dimension(session: Session, scope, filters: AnalyticsFilters, dimension: str) -> tuple[list[dict], list[dict]]:
    fields = {"house": CanonicalWork.house, "state": CanonicalWork.state_name}
    works = active_works_statement(scope, filters).subquery()
    field = works.c[fields[dimension].key]
    total_rows = session.execute(
        select(field.label("dimension"), func.count(distinct(works.c.canonical_work_key)).label("work_count"))
        .select_from(works)
        .group_by(field)
    ).all()

    def linked_counts(model) -> dict[Any, int]:
        rows = session.execute(
            select(field.label("dimension"), func.count(distinct(model.canonical_work_key)).label("count"))
            .select_from(works.join(model, model.canonical_work_key == works.c.canonical_work_key).join(DatasetVersion, model.source_dataset_version_id == DatasetVersion.id))
            .where(DatasetVersion.batch_id == scope.batch_id)
            .group_by(field)
        ).all()
        return {row.dimension: int(row.count) for row in rows}

    sanctioned, completed = linked_counts(SanctionedWorkRecord), linked_counts(CompletedWorkRecord)
    rows = [
        {
            "label": _display(row.dimension, house=dimension == "house"),
            "sanctioned": sanctioned.get(row.dimension, 0),
            "completed": completed.get(row.dimension, 0),
            "work_count": int(row.work_count),
        }
        for row in total_rows
    ]
    rows.sort(key=lambda row: (-int(row["work_count"]), row["label"]))
    return rows, [{"key": "sanctioned", "label": "Sanctioned works"}, {"key": "completed", "label": "Completed works"}]


def _status_by_house_matrix(session: Session, scope, filters: AnalyticsFilters) -> tuple[list[dict], list[dict]]:
    works = active_works_statement(scope, filters).subquery()
    source_rows = session.execute(
        select(
            works.c.house.label("house"),
            SanctionedWorkRecord.work_status_source.label("source_status"),
            func.count(distinct(SanctionedWorkRecord.canonical_work_key)).label("work_count"),
        )
        .select_from(works.join(SanctionedWorkRecord, SanctionedWorkRecord.canonical_work_key == works.c.canonical_work_key).join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id))
        .where(DatasetVersion.batch_id == scope.batch_id)
        .group_by(works.c.house, SanctionedWorkRecord.work_status_source)
    ).all()
    if not source_rows:
        return [], []
    statuses = sorted({row.source_status if row.source_status else "Not available" for row in source_rows})
    keys = {status: f"status_{index}" for index, status in enumerate(statuses)}
    matrix: dict[str, dict[str, int]] = defaultdict(dict)
    for row in source_rows:
        status = row.source_status if row.source_status else "Not available"
        matrix[row.house][keys[status]] = int(row.work_count)
    rows = [
        {"label": _display(house, house=True), "value": sum(values.values()), **{key: values.get(key, 0) for key in keys.values()}}
        for house, values in sorted(matrix.items())
    ]
    return rows, [{"key": keys[status], "label": status} for status in statuses]


def _state_category_matrix(session: Session, scope, filters: AnalyticsFilters) -> tuple[list[dict], list[dict]]:
    works = active_works_statement(scope, filters).subquery()
    source_rows = session.execute(
        select(
            works.c.state_name.label("state"),
            works.c.work_category_source.label("category"),
            func.count(distinct(works.c.canonical_work_key)).label("work_count"),
        )
        .select_from(works)
        .group_by(works.c.state_name, works.c.work_category_source)
        .order_by(func.count(distinct(works.c.canonical_work_key)).desc())
    ).all()
    if not source_rows:
        return [], []
    state_totals: dict[Any, int] = defaultdict(int)
    category_totals: dict[Any, int] = defaultdict(int)
    matrix: dict[Any, dict[Any, int]] = defaultdict(dict)
    for row in source_rows:
        state_totals[row.state] += int(row.work_count)
        category_totals[row.category] += int(row.work_count)
        matrix[row.state][row.category] = int(row.work_count)
    states = sorted(state_totals, key=lambda value: (-state_totals[value], _display(value)))[:_MAX_HEATMAP_STATES]
    categories = sorted(category_totals, key=lambda value: (-category_totals[value], _display(value)))[:_MAX_HEATMAP_CATEGORIES]
    category_keys = {category: f"category_{index}" for index, category in enumerate(categories)}
    rows = [
        {
            "label": _display(state),
            "value": sum(matrix[state].get(category, 0) for category in categories),
            **{category_keys[category]: matrix[state].get(category, 0) for category in categories},
        }
        for state in states
    ]
    return rows, [{"key": category_keys[category], "label": _display(category)} for category in categories]


def _observed_completion_durations(session: Session, scope, filters: AnalyticsFilters) -> list[float]:
    work_keys = active_works_statement(scope, filters).with_only_columns(CanonicalWork.canonical_work_key).subquery()
    sanction_dates = (
        select(SanctionedWorkRecord.canonical_work_key.label("key"), func.min(SanctionedWorkRecord.sanction_date).label("sanction_date"))
        .join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id)
        .join(work_keys, SanctionedWorkRecord.canonical_work_key == work_keys.c.canonical_work_key)
        .where(DatasetVersion.batch_id == scope.batch_id, SanctionedWorkRecord.sanction_date.is_not(None))
        .group_by(SanctionedWorkRecord.canonical_work_key)
        .subquery()
    )
    completion_dates = (
        select(CompletedWorkRecord.canonical_work_key.label("key"), func.min(CompletedWorkRecord.completion_date).label("completion_date"))
        .join(DatasetVersion, CompletedWorkRecord.source_dataset_version_id == DatasetVersion.id)
        .join(work_keys, CompletedWorkRecord.canonical_work_key == work_keys.c.canonical_work_key)
        .where(DatasetVersion.batch_id == scope.batch_id, CompletedWorkRecord.completion_date.is_not(None))
        .group_by(CompletedWorkRecord.canonical_work_key)
        .subquery()
    )
    statement = select((func.julianday(completion_dates.c.completion_date) - func.julianday(sanction_dates.c.sanction_date)).label("duration")).select_from(sanction_dates.join(completion_dates, completion_dates.c.key == sanction_dates.c.key))
    return [float(row.duration) for row in session.execute(statement) if row.duration is not None and row.duration >= 0]


def _histogram_rows(values: list[float]) -> list[dict]:
    if not values:
        return []
    minimum, maximum = min(values), max(values)
    if minimum == maximum:
        return [{"label": f"{minimum:g} days", "bin_start": minimum, "bin_end": maximum, "value": len(values)}]
    bin_count = min(12, max(2, ceil(sqrt(len(values)))))
    width = (maximum - minimum) / bin_count
    counts = [0] * bin_count
    for value in values:
        index = min(int((value - minimum) / width), bin_count - 1)
        counts[index] += 1
    rows = []
    for index, count in enumerate(counts):
        start = minimum + index * width
        end = maximum if index == bin_count - 1 else minimum + (index + 1) * width
        rows.append({"label": f"{start:g}–{end:g} days", "bin_start": start, "bin_end": end, "value": count})
    return rows


def explore_visualization(session: Session, metric: str, group_by: str, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    """Select a chart only where the active-release result supports that visual form."""
    metric, group_by = metric.lower(), group_by.lower()
    if metric not in _METRICS or group_by not in _GROUPS:
        raise ValueError("Unsupported visualization metric or grouping.")
    scope = resolve_active_scope(session)

    if metric == "works":
        if group_by == "summary":
            metrics = core_metrics(session, filters).data
            return _result(scope, filters, title="Canonical works", description="Distinct canonical work records in the current active selection.", chart_type="KPI", x_axis=None, y_axis=None, unit="Works", series=[], rows=[{"label": "Canonical works", "value": metrics["total_canonical_works"]}], record_count=1, data_available=True, selection=_selection("single_verified_metric", "A single aggregate is most accurately shown as a KPI."))
        if group_by == "house":
            rows = [{"label": _display(row["house"], house=True), "value": row["total_canonical_works"]} for row in house_comparison(session, AnalyticsFilters(**{**filters.as_dict(), "house": None})).data["rows"]]
            return _category_spec(scope, filters, "Works by House", "Share of canonical work records across Houses.", rows, chart_type="PIE", unit="Works", x_axis="House", y_axis="Works", selection_rule="small_category_share", selection_rationale="A small mutually exclusive House share is shown as a pie chart.")
        if group_by == "status":
            rows = [{"label": row["source_status"] or "Not available", "value": row["work_count"]} for row in status_distribution(session, filters).data["rows"]]
            return _category_spec(scope, filters, "Works by source status", "Source status labels are preserved without remapping.", rows, chart_type="DONUT", unit="Works", x_axis="Source status", y_axis="Works", selection_rule="categorical_share", selection_rationale="Observed source-status counts form a categorical share.")
        if group_by == "period":
            trend = works_trend(session, filters).data
            if not trend["data_available"]:
                return _unavailable(scope, filters, "Works over time", "Trend unavailable for the selected data.", rule="dated_observation_required")
            rows = [{"label": row["period"], "value": row["record_count"]} for row in trend["rows"]]
            return _category_spec(scope, filters, "Works over time", "Date-backed monthly recommendation records.", rows, chart_type="LINE", unit="Works", x_axis="Period", y_axis="Works", selection_rule="dated_sequence", selection_rationale="Observed monthly records are ordered chronologically without filling missing periods.")
        if group_by == "work":
            return _category_spec(scope, filters, "Work detail counts", "Detailed work records remain available as a table.", _works_by_work(session, scope, filters), chart_type="TABLE", unit="Works", x_axis="Work", y_axis="Works", selection_rule="high_cardinality_detail", selection_rationale="High-cardinality work identifiers are retained as a table.")
        if group_by == "state_category":
            rows, series = _state_category_matrix(session, scope, filters)
            if not rows:
                return _unavailable(scope, filters, "Works by State and source category", "No records match the selected filters.", rule="category_matrix")
            return _result(scope, filters, title="Works by State and source category", description=f"Displayed matrix uses the top {_MAX_HEATMAP_STATES} states and {_MAX_HEATMAP_CATEGORIES} observed source categories by work count.", chart_type="HEATMAP", x_axis="Source work category", y_axis="State / UT", unit="Works", series=series, rows=rows, record_count=len(rows), data_available=True, selection=_selection("category_matrix", "Two observed categorical dimensions form a State/category count matrix."))
        if group_by in {"state", "district_or_ida", "mp"}:
            summary = summarize_by(session, group_by, filters).data
            rows = [{"label": row["value"] or "Not available", "value": row["work_count"]} for row in summary["rows"]]
            title = f"Works by {group_by.replace('_', ' ').title()}"
            return _category_spec(scope, filters, title, "Ranked canonical work counts from the active dataset.", rows, chart_type="HORIZONTAL_BAR", unit="Works", x_axis="Works", y_axis=group_by.replace("_", " ").title(), selection_rule="ranked_categories", selection_rationale="Many observed categories are easier to compare in a ranked horizontal bar chart.")

    if metric == "expenditure":
        if group_by == "period":
            trend = expenditure_trend(session, filters).data
            if not trend["data_available"]:
                return _unavailable(scope, filters, "Expenditure over time", "Trend unavailable for the selected data.", rule="dated_observation_required")
            rows = [{"label": row["period"], "value": _number(row.get("amount"))} for row in trend["rows"]]
            return _category_spec(scope, filters, "Expenditure over time", "Date-backed expenditure transactions by month.", rows, chart_type="AREA", unit="Expenditure", x_axis="Period", y_axis="Expenditure", selection_rule="dated_amount_sequence", selection_rationale="Observed monthly monetary totals are ordered chronologically; no missing periods are synthesized.")
        if group_by not in {"house", "state", "district_or_ida", "mp", "work"}:
            raise ValueError("Expenditure must be grouped by House, State, District / IDA, MP, Work, or period.")
        values = expenditure_by(session, group_by, filters).data["rows"]
        rows = [{"label": row["value"] or "Not available", "value": _number(row["expenditure"]), "transaction_count": row["transaction_count"]} for row in values]
        chart_type = "DONUT" if group_by == "house" else "HORIZONTAL_BAR"
        title = f"Expenditure by {group_by.replace('_', ' ').title()}"
        rationale = "House expenditure is a small categorical share." if group_by == "house" else "Many observed categories are ranked by recorded expenditure."
        return _category_spec(scope, filters, title, "Recorded expenditure transactions from the active dataset.", rows, chart_type=chart_type, unit="Expenditure", x_axis="Expenditure" if chart_type == "HORIZONTAL_BAR" else group_by.replace("_", " ").title(), y_axis=group_by.replace("_", " ").title() if chart_type == "HORIZONTAL_BAR" else "Expenditure", selection_rule="categorical_share" if group_by == "house" else "ranked_categories", selection_rationale=rationale)

    if metric == "status":
        if group_by == "status" or group_by == "summary":
            rows = [{"label": row["source_status"] or "Not available", "value": row["work_count"]} for row in status_distribution(session, filters).data["rows"]]
            return _category_spec(scope, filters, "Source work-status distribution", "Source status labels are not semantically remapped.", rows, chart_type="DONUT", unit="Works", x_axis="Source status", y_axis="Works", selection_rule="categorical_share", selection_rationale="Observed source-status counts form a categorical share.")
        if group_by == "house":
            rows, series = _status_by_house_matrix(session, scope, filters)
            if not rows:
                return _unavailable(scope, filters, "Source work status by House", "No records match the selected filters.", rule="category_composition")
            return _result(scope, filters, title="Source work status by House", description="Source status labels are preserved and stacked within each observed House.", chart_type="STACKED_BAR", x_axis="House", y_axis="Works", unit="Works", series=series, rows=rows, record_count=len(rows), data_available=True, selection=_selection("category_composition", "Each House contains observed source-status categories, so a stacked bar shows their composition."))
        raise ValueError("Source status can only be shown as a status distribution or by House.")

    if metric == "progress":
        if group_by not in {"house", "state"}:
            raise ValueError("Observed work progress can only be grouped by House or State / UT.")
        rows, series = _progress_by_dimension(session, scope, filters, group_by)
        title = f"Sanctioned and completed works by {group_by.replace('_', ' ').title()}"
        if not rows:
            return _unavailable(scope, filters, title, "No records match the selected filters.", rule="two_metric_category_comparison")
        return _result(scope, filters, title=title, description="Distinct linked sanction and completion records from the active dataset are compared side by side.", chart_type="GROUPED_BAR", x_axis=group_by.replace("_", " ").title(), y_axis="Works", unit="Works", series=series, rows=rows, record_count=len(rows), data_available=True, selection=_selection("two_metric_category_comparison", "Two observed work-linkage counts are compared for each category."))

    if metric == "lifecycle":
        if group_by == "summary":
            lifecycle = lifecycle_summary(session, filters).data
            rows = [
                {"label": "Recommendation to sanction median days", "value": lifecycle["recommendation_to_sanction"]["median_days"], "count": lifecycle["recommendation_to_sanction"]["count_with_both_dates"]},
                {"label": "Sanction to completion median days", "value": lifecycle["sanction_to_completion"]["median_days"], "count": lifecycle["sanction_to_completion"]["count_with_both_dates"]},
            ]
            rows = [row for row in rows if row["value"] is not None]
            return _category_spec(scope, filters, "Observed lifecycle duration", "Only records with both source dates contribute to each observed duration.", rows, chart_type="BAR", unit="Days", x_axis="Lifecycle stage", y_axis="Median days", selection_rule="small_metric_comparison", selection_rationale="Two observed lifecycle median measures are compared directly.")
        if group_by == "distribution":
            rows = _histogram_rows(_observed_completion_durations(session, scope, filters))
            return _category_spec(scope, filters, "Observed sanction-to-completion duration distribution", "Equal-width bins are calculated from observed source dates only.", rows, chart_type="HISTOGRAM", unit="Works", x_axis="Observed duration (days)", y_axis="Works", selection_rule="observed_numeric_distribution", selection_rationale="Observed non-negative duration values are binned for a frequency distribution.")
        raise ValueError("Observed lifecycle metrics are available as a summary or observed duration distribution.")

    if metric == "relationship":
        if group_by != "state":
            raise ValueError("The supported relationship view compares canonical work count and expenditure by State / UT.")
        summary = summarize_by(session, "state", filters).data["rows"]
        rows = [{"label": row["value"] or "Not available", "x": int(row["work_count"]), "y": _number(row["expenditure"])} for row in summary]
        if len(rows) < 2:
            return _unavailable(scope, filters, "Works and expenditure by State / UT", "A metric relationship requires at least two observed State / UT groups.", rule="two_numeric_metrics")
        return _result(scope, filters, title="Works and expenditure by State / UT", description="Each point is one active-release State / UT aggregate; the chart does not infer correlation or causation.", chart_type="SCATTER", x_axis="Canonical works", y_axis="Recorded expenditure", unit="Expenditure", series=[{"key": "y", "label": "Recorded expenditure"}], rows=rows, record_count=len(rows), data_available=True, selection=_selection("two_numeric_metrics", "Two observed numeric aggregates are compared for each State / UT."))

    raise ValueError("Unsupported visualization request.")


def _tool_matrix(values: list[dict[str, Any]], *, group_key: str, category_key: str, value_key: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Convert already-verified long-form category counts to a display matrix."""
    categories = sorted({str(row.get(category_key) or "Not available") for row in values if isinstance(row, dict)})
    keys = {category: f"series_{index}" for index, category in enumerate(categories)}
    grouped: dict[str, dict[str, int | float]] = {}
    for row in values:
        if not isinstance(row, dict):
            continue
        group = str(row.get(group_key) or "Not available")
        category = str(row.get(category_key) or "Not available")
        grouped.setdefault(group, {})[keys[category]] = _number(row.get(value_key, 0))
    rows = [
        {"label": group, "value": sum(values.values()), **{key: values.get(key, 0) for key in keys.values()}}
        for group, values in sorted(grouped.items())
    ]
    return rows, [{"key": keys[category], "label": category} for category in categories]


def visualization_from_verified_tool(tool_name: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Create an optional chart spec from an already-verified Ask AI tool result.

    This performs no queries and never changes the provider payload. It only uses compact,
    authoritative values already returned by the backend tool registry.
    """
    values = data.get("works_by_house")
    if isinstance(values, list) and values:
        rows = [{"label": str(row.get("house", "Not available")).replace("_", " "), "value": _number(row.get("work_count", 0))} for row in values if isinstance(row, dict)]
        if rows:
            return {"title": "Works by House", "description": "Counts are from the verified active-release tool result.", "chart_type": "PIE", "x_axis": "House", "y_axis": "Works", "unit": "Works", "series": [{"key": "value", "label": "Works"}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection("small_category_share", "A small mutually exclusive House share is shown as a pie chart.", source="verified_tool_result")}
    values = data.get("works_by_state")
    if isinstance(values, list) and values:
        rows = [{"label": str(row.get("state", "Not available")), "value": _number(row.get("work_count", 0))} for row in values if isinstance(row, dict)]
        if rows:
            return {"title": "Works by State / UT", "description": "Counts are from the verified active-release tool result.", "chart_type": "HORIZONTAL_BAR", "x_axis": "Works", "y_axis": "State / UT", "unit": "Works", "series": [{"key": "value", "label": "Works"}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection("ranked_categories", "Observed State / UT work counts are ranked.", source="verified_tool_result")}
    values = data.get("work_status_distribution")
    if isinstance(values, list) and values:
        rows = [{"label": str(row.get("status", "Not available")), "value": _number(row.get("work_count", 0))} for row in values if isinstance(row, dict)]
        if rows:
            return {"title": "Source work-status distribution", "description": "Source status labels are preserved from the verified tool result.", "chart_type": "DONUT", "x_axis": "Source status", "y_axis": "Works", "unit": "Works", "series": [{"key": "value", "label": "Works"}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection("categorical_share", "Verified source-status counts form a categorical share.", source="verified_tool_result")}
    values = data.get("sanction_to_completion_duration_distribution")
    if isinstance(values, list) and values:
        rows = [{"label": f"{_number(row.get('bin_start', 0)):g}–{_number(row.get('bin_end', 0)):g} days", "bin_start": _number(row.get("bin_start", 0)), "bin_end": _number(row.get("bin_end", 0)), "value": _number(row.get("work_count", 0))} for row in values if isinstance(row, dict)]
        if rows:
            return {"title": "Observed sanction-to-completion duration distribution", "description": "Equal-width bins are calculated only from observed source dates in the verified tool result.", "chart_type": "HISTOGRAM", "x_axis": "Observed duration (days)", "y_axis": "Works", "unit": "Works", "series": [{"key": "value", "label": "Works"}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection("observed_numeric_distribution", "Verified non-negative observed durations are binned for frequency display.", source="verified_tool_result")}
    for key, group_key, title in (("work_status_by_house", "house", "Source work status by House"), ("work_status_by_state", "state", "Source work status by State / UT")):
        values = data.get(key)
        if isinstance(values, list) and values:
            rows, series = _tool_matrix(values, group_key=group_key, category_key="status", value_key="work_count")
            if rows:
                return {"title": title, "description": "Source status labels are preserved from the verified tool result.", "chart_type": "STACKED_BAR", "x_axis": group_key.replace("_", " ").title(), "y_axis": "Works", "unit": "Works", "series": series, "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection("category_composition", "Observed source-status categories are stacked within each group.", source="verified_tool_result")}
    for key, group_key, title in (("sanctioned_completed_by_house", "house", "Sanctioned and completed works by House"), ("sanctioned_completed_by_state", "state", "Sanctioned and completed works by State / UT")):
        values = data.get(key)
        if isinstance(values, list) and values:
            rows = [{"label": str(row.get(group_key, "Not available")).replace("_", " ") if group_key == "house" else str(row.get(group_key, "Not available")), "sanctioned": _number(row.get("sanctioned", 0)), "completed": _number(row.get("completed", 0)), "work_count": _number(row.get("work_count", 0))} for row in values if isinstance(row, dict)]
            if rows:
                return {"title": title, "description": "Distinct linked sanction and completion counts are from the verified tool result.", "chart_type": "GROUPED_BAR", "x_axis": group_key.replace("_", " ").title(), "y_axis": "Works", "unit": "Works", "series": [{"key": "sanctioned", "label": "Sanctioned works"}, {"key": "completed", "label": "Completed works"}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection("two_metric_category_comparison", "Two verified work-linkage counts are compared for each group.", source="verified_tool_result")}
    for key, label_key, value_key, title, chart_type, unit, rule, rationale in (
        ("sanctioned_amount_by_house", "house", "sanction_amount", "Sanctioned amount by House", "DONUT", "Sanction amount", "categorical_share", "House sanction amounts form a small categorical share."),
        ("allocation_by_house", "house", "allocation", "Allocation by House", "DONUT", "Allocation", "categorical_share", "House allocation amounts form a small categorical share."),
    ):
        values = data.get(key)
        if isinstance(values, list) and values:
            rows = [{"label": str(row.get(label_key, "Not available")).replace("_", " "), "value": _number(row.get(value_key, 0))} for row in values if isinstance(row, dict)]
            if rows:
                return {"title": title, "description": "Amounts are from the verified active-release tool result.", "chart_type": chart_type, "x_axis": label_key.replace("_", " ").title(), "y_axis": unit, "unit": unit, "series": [{"key": "value", "label": unit}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection(rule, rationale, source="verified_tool_result")}
    values = data.get("allocation_vs_expenditure_by_house")
    if isinstance(values, list) and values:
        rows = [{"label": str(row.get("house", "Not available")).replace("_", " "), "allocation": _number(row.get("allocation", 0)), "expenditure": _number(row.get("expenditure", 0))} for row in values if isinstance(row, dict)]
        if rows:
            return {"title": "Allocation and expenditure by House", "description": "Both monetary amounts are from the verified active-release tool result.", "chart_type": "GROUPED_BAR", "x_axis": "House", "y_axis": "Amount", "unit": "Expenditure", "series": [{"key": "allocation", "label": "Allocation"}, {"key": "expenditure", "label": "Recorded expenditure"}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection("two_metric_category_comparison", "Two verified monetary aggregates are compared for each House.", source="verified_tool_result")}
    tabular = (
        ("top_states_by_expenditure", "state", "expenditure", "Top states by recorded expenditure", "HORIZONTAL_BAR", "Expenditure", "ranked_categories", "Observed State / UT expenditure values are ranked."),
        ("expenditure_by_house", "house", "expenditure", "Recorded expenditure by House", "DONUT", "Expenditure", "categorical_share", "House expenditure is a small categorical share."),
    )
    for key, label_key, value_key, title, chart_type, unit, rule, rationale in tabular:
        values = data.get(key)
        if isinstance(values, list) and values:
            rows = [{"label": str(row.get(label_key, "Not available")), "value": _number(row.get(value_key, 0))} for row in values if isinstance(row, dict)]
            if rows:
                return {"title": title, "description": "Values are from the verified backend tool result.", "chart_type": chart_type, "x_axis": label_key.replace("_", " ").title(), "y_axis": unit, "unit": unit, "series": [{"key": "value", "label": unit}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection(rule, rationale, source="verified_tool_result")}
    for key, title in (("risk_distribution", "Risk distribution"), ("alert_severity_distribution", "Alert severity distribution"), ("recommendations_by_status", "Recommendation status distribution"), ("review_cases_by_status", "Review-case status distribution")):
        values = data.get(key)
        if isinstance(values, dict) and values:
            rows = [{"label": str(label), "value": _number(value)} for label, value in values.items()]
            return {"title": title, "description": "Counts are from the verified backend tool result.", "chart_type": "DONUT", "x_axis": "Category", "y_axis": "Count", "unit": "Count", "series": [{"key": "value", "label": "Count"}], "rows": rows, "record_count": len(rows), "data_available": True, "selection": _selection("categorical_share", "Verified category counts form a share of the verified result.", source="verified_tool_result")}
    scalar_keys = ("monitored_works", "completed_works", "available_comparisons", "potential_bottlenecks", "potential_duplicate_candidates")
    for key in scalar_keys:
        if key in data and isinstance(data[key], (int, float)):
            return {"title": key.replace("_", " ").title(), "description": "Value is from the verified backend tool result.", "chart_type": "KPI", "x_axis": None, "y_axis": None, "unit": "Count", "series": [], "rows": [{"label": key.replace("_", " ").title(), "value": data[key]}], "record_count": 1, "data_available": True, "selection": _selection("single_verified_metric", "A single verified value is most accurately shown as a KPI.", source="verified_tool_result")}
    return None
