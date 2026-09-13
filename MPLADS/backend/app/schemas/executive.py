"""Typed contracts for protected executive decision-support summaries."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.intelligence import ProtectedProvenance


class ExecutiveSummary(BaseModel):
    total_monitored_works: int
    total_signals: int
    total_alerts: int
    high_priority_alerts: int
    high_priority_risk_works: int
    review_backlog: dict[str, int]
    active_escalations: int
    available_benchmarks: int
    benchmark_bottlenecks: int
    active_recommendations: int
    recommendations_by_priority: dict[str, int]
    recommendations_by_status: dict[str, int]
    provenance: ProtectedProvenance


class ExecutiveAttention(BaseModel):
    level: str
    signal_count: int
    drivers: list[dict[str, Any]]
    high_priority_categories: dict[str, int]
    scope: dict[str, str | None]
    provenance: ProtectedProvenance


class ExecutiveTrend(BaseModel):
    category: str
    current_value: int
    previous_value: int | None
    absolute_change: int | None
    percentage_change: float | None


class ExecutiveTrends(BaseModel):
    available: bool
    message: str | None
    rows: list[ExecutiveTrend]
    provenance: ProtectedProvenance


class ExecutiveGeography(BaseModel):
    rows: list[dict[str, Any]]
    material_concentration: bool
    message: str | None
    provenance: ProtectedProvenance


class ExecutiveComparison(BaseModel):
    rows: list[dict[str, Any]]
    provenance: ProtectedProvenance


class ExecutiveDrilldown(BaseModel):
    summary: ExecutiveSummary
    priority_queue: list[dict[str, Any]]
    links: dict[str, str]
    provenance: ProtectedProvenance
