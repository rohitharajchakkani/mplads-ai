from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProtectedProvenance(BaseModel):
    dataset_version: str
    generated_at: datetime
    rules_version: str | None = None
    model_version: str | None = None


class RiskWorkResponse(BaseModel):
    work_key: str
    house: str
    state_name: str | None
    district_or_ida: str | None
    mp_source_name: str | None
    raw_score: int
    normalized_score: float
    risk_band: str
    component_scores: dict[str, Any]
    evidence: dict[str, Any]
    data_quality_context: dict[str, Any]
    provenance: ProtectedProvenance


class RiskSummaryResponse(BaseModel):
    total_assessments: int
    risk_distribution: dict[str, int]
    signals_by_category: dict[str, int]
    alerts_by_severity: dict[str, int]
    high_priority_works: int
    provenance: ProtectedProvenance


class AlertResponse(BaseModel):
    alert_id: str
    work_key: str
    house: str
    state_name: str | None = None
    district_or_ida: str | None = None
    mp_source_name: str | None = None
    category: str
    severity: str
    title: str
    explanation: str
    evidence: dict[str, Any]
    status: str
    generated_at: datetime
    provenance: ProtectedProvenance


class AlertSummaryResponse(BaseModel):
    total_alerts: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    provenance: ProtectedProvenance


class DuplicateCandidateResponse(BaseModel):
    candidate_id: str
    work_a_key: str
    work_b_key: str
    similarity_score: float
    review_priority: str
    contextual_comparison: dict[str, Any]
    reason: str
    generated_at: datetime
    provenance: ProtectedProvenance


class AnomalySummaryResponse(BaseModel):
    total_ml_anomaly_signals: int
    model_version: str
    dataset_version: str
    generated_at: datetime


class ProtectedPage(BaseModel):
    items: list[Any]
    pagination: dict[str, int]
    provenance: ProtectedProvenance


class MonitoringCategoryResponse(BaseModel):
    category: str
    total_signals: int
    by_severity: dict[str, int]
    by_house: dict[str, int]
    by_state: dict[str, int]
    related_category_counts: dict[str, int] = Field(default_factory=dict)
    financial_patterns: dict[str, Any] | None = None
    observed_lifecycle: dict[str, Any] | None = None
    provenance: ProtectedProvenance
