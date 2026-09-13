"""Formal allowlist for all read-only Ask AI database tools."""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Literal, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ToolArguments(BaseModel):
    """Only database-backed, equality filters accepted by the tool boundary."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    house: str | None = Field(default=None, min_length=1, max_length=20)
    state: str | None = Field(default=None, min_length=1, max_length=150)
    district_or_ida: str | None = Field(default=None, min_length=1, max_length=500)
    mp: str | None = Field(default=None, min_length=1, max_length=300)
    constituency: str | None = Field(default=None, min_length=1, max_length=300)
    work_key: str | None = Field(default=None, min_length=1, max_length=110)
    view: Literal[
        "SUMMARY", "WORKS_BY_HOUSE", "WORKS_BY_STATE", "WORK_STATUS_BY_HOUSE",
        "WORK_STATUS_BY_STATE", "SANCTIONED_COMPLETED_BY_HOUSE",
        "SANCTIONED_COMPLETED_BY_STATE", "WORK_STATUS_DISTRIBUTION", "COMPLETION_RATIO",
        "LIFECYCLE_DURATION_DISTRIBUTION", "FINANCIAL_SUMMARY",
        "SANCTIONED_AMOUNT_BY_HOUSE", "ALLOCATION_BY_HOUSE",
        "ALLOCATION_VS_EXPENDITURE_BY_HOUSE",
    ] | None = None
    limit: int = Field(default=10, ge=1, le=25)


class ToolResult(BaseModel):
    """Normalized boundary between verified results and Gemini explanation."""
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    success: bool
    data: dict
    result_count: int
    truncated: bool = False
    filters_applied: dict[str, str | int | None]
    scope: dict[str, str | None]
    dataset_version: str
    generated_at: str
    warnings: list[str] = Field(default_factory=list)
    navigation_links: list[dict[str, str]] = Field(default_factory=list)


@dataclass(frozen=True)
class ToolSpec:
    tool_name: str
    description: str
    argument_schema: Type[BaseModel]
    allowed_roles: FrozenSet[str]
    scope_requirements: FrozenSet[str]
    maximum_result_size: int
    supported_entity_types: FrozenSet[str]
    supported_filters: FrozenSet[str]
    read_only: bool = True


_ROLES = frozenset({"MP", "DISTRICT_AUTHORITY", "STATE_NODAL_AUTHORITY", "MINISTRY", "PLATFORM_ADMINISTRATOR"})
_FILTERS = frozenset({"house", "state", "district_or_ida", "mp", "constituency", "work_key", "view", "limit"})
_SUMMARY_ENTITIES = frozenset({"STATE", "DISTRICT", "MP", "CONSTITUENCY", "WORK"})


def _spec(name: str, description: str, *, entities: FrozenSet[str] = _SUMMARY_ENTITIES, filters: FrozenSet[str] = _FILTERS) -> ToolSpec:
    return ToolSpec(
        tool_name=name,
        description=description,
        argument_schema=ToolArguments,
        allowed_roles=_ROLES,
        scope_requirements=frozenset({"ACTIVE_RELEASE", "AUTHORIZED_INTELLIGENCE_SCOPE"}),
        maximum_result_size=25,
        supported_entity_types=entities,
        supported_filters=filters,
        read_only=True,
    )


# This is deliberately a small allowlist. A tool is listed only when it has an
# implemented handler in app.ai.tools and reads persisted MPLADS evidence.
TOOL_REGISTRY: dict[str, ToolSpec] = {
    spec.tool_name: spec
    for spec in (
        _spec("get_dashboard_summary", "Count authorized monitored works in the active release."),
        _spec("get_work_summary", "Return bounded, authorized active-release work counts and selected work distributions."),
        _spec("get_financial_by_state", "Return a bounded, authorized state expenditure aggregation."),
        _spec("get_financial_by_house", "Return a bounded, authorized House expenditure aggregation."),
        _spec("get_financial_summary", "Return authorized expenditure, sanction, and allocation summaries.", filters=_FILTERS - {"district_or_ida", "constituency", "work_key"}),
        _spec("get_lifecycle_summary", "Count authorized completed works from active source records."),
        _spec("get_duplicate_summary", "Count authorized persisted potential duplicate candidates.", filters=frozenset({"limit"})),
        _spec("get_risk_summary", "Return authorized persisted risk-band counts."),
        _spec("get_monitoring_signal_detail", "Return a bounded, authorized monitoring-signal detail for a work."),
        _spec("get_alert_summary", "Return authorized persisted alert-severity counts."),
        _spec("get_recommendations", "Return authorized persisted recommendation-status counts."),
        _spec("get_review_summary", "Return authorized persisted review-case status counts."),
        _spec("get_benchmark_result", "Return authorized peer-comparison and bottleneck counts.", filters=_FILTERS - {"constituency", "work_key"}),
        _spec("get_executive_summary", "Return authorized national or scoped executive evidence counts.", filters=_FILTERS - {"constituency", "work_key"}),
    )
}


def get_tool(tool_name: str) -> ToolSpec:
    try:
        return TOOL_REGISTRY[tool_name]
    except KeyError as exc:
        raise ValueError("Unknown or unauthorized AI tool.") from exc


def validate_tool_arguments(tool_name: str, arguments: dict) -> ToolArguments:
    spec = get_tool(tool_name)
    if not spec.read_only:
        raise ValueError("AI write tools are not available.")
    if set(arguments) - spec.supported_filters:
        raise ValueError("Unsupported AI tool argument.")
    try:
        parsed = spec.argument_schema.model_validate(arguments)
    except ValidationError as exc:
        raise ValueError("Invalid AI tool arguments.") from exc
    if parsed.limit > spec.maximum_result_size:
        raise ValueError("Requested result limit exceeds the approved tool maximum.")
    return parsed
