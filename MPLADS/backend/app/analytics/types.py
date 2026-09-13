from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AnalyticsFilters:
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

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class Provenance:
    service: str
    release_version: str
    batch_id: str
    filters: dict[str, str | None]
    generated_at: str


@dataclass(frozen=True)
class AnalyticsResult:
    data: dict[str, Any]
    provenance: Provenance


def provenance(service: str, scope, filters: AnalyticsFilters) -> Provenance:
    return Provenance(service, scope.release_version, scope.batch_id, filters.as_dict(), datetime.now(UTC).isoformat())
