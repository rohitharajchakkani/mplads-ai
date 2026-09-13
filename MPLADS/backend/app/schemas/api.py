from typing import Any

from pydantic import BaseModel, Field


class Filters(BaseModel):
    house: str | None = None
    state: str | None = None
    district_or_ida: str | None = None
    mp: str | None = None
    work: str | None = None
    constituency: str | None = None
    financial_year: str | None = None
    sector: str | None = None
    subsector: str | None = None
    work_status: str | None = None


class ProvenanceResponse(BaseModel):
    service: str
    release_version: str
    batch_id: str
    filters: dict[str, str | None]
    generated_at: str


class AnalyticsResponse(BaseModel):
    data: dict[str, Any]
    provenance: ProvenanceResponse


class PageMeta(BaseModel):
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_pages: int


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]]
    pagination: PageMeta
    provenance: ProvenanceResponse


class HealthResponse(BaseModel):
    status: str
    database_status: str
    active_dataset_status: str
    active_release_version: str | None
    migration_version: str | None
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
