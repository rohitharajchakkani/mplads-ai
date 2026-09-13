from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.intelligence import ProtectedProvenance


class BenchmarkResultResponse(BaseModel):
    result_id: str
    entity_type: str
    entity_id: str
    house: str
    state_name: str | None
    district_or_ida: str | None
    mp_source_name: str | None
    metric: str
    formula: str
    metric_details: dict[str, Any] | None
    value: float | None
    peer_median: float | None
    p25: float | None
    p75: float | None
    p90: float | None
    iqr: float | None
    peer_count: int
    valid_work_count: int
    benchmark_available: bool
    unavailable_reason: str | None
    directionality: str
    bottleneck_flag: bool
    interpretation: str
    dataset_version: str
    benchmark_version: str
    provenance_hash: str
    generated_at: datetime


class BenchmarkPage(BaseModel):
    items: list[BenchmarkResultResponse]
    pagination: dict[str, int]
    provenance: ProtectedProvenance


class BenchmarkSummary(BaseModel):
    run_id: str
    entity_count: int
    result_count: int
    by_metric: dict[str, int]
    bottleneck_count: int
    benchmark_version: str
    dataset_version: str
    generated_at: datetime


class BenchmarkPeers(BaseModel):
    result_id: str
    cohort_definition: dict[str, Any]
    peer_ids: list[str]
    peer_count: int
    provenance: ProtectedProvenance


class RecommendationResponse(BaseModel):
    recommendation_id: str
    canonical_work_key: str | None
    entity_type: str
    entity_id: str
    house: str | None
    state_name: str | None
    district_or_ida: str | None
    mp_source_name: str | None
    recommendation_type: str
    reason: str
    evidence_references: dict[str, Any]
    priority: str
    dataset_version: str
    status: str
    generated_at: datetime
    updated_at: datetime
    version: int


class RecommendationPage(BaseModel):
    items: list[RecommendationResponse]
    pagination: dict[str, int]
    provenance: ProtectedProvenance


class RecommendationStatusRequest(BaseModel):
    status: str
    version: int = Field(ge=1)
