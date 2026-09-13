"""Source-preserving, deterministic normalization for audited MPLADS schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ingestion.audit import normalized_work_id

DATE_FORMAT = "%d-%b-%Y"


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).strip().split())
    return cleaned or None


def parse_money(value: Any) -> tuple[Decimal | None, str | None]:
    cleaned = clean_text(value)
    if cleaned is None:
        return None, "MISSING_MONEY"
    try:
        return Decimal(cleaned.replace(",", "")), None
    except InvalidOperation:
        return None, "MALFORMED_MONEY"


def parse_date(value: Any) -> tuple[str | None, str | None]:
    cleaned = clean_text(value)
    if cleaned is None:
        return None, "MISSING_DATE"
    try:
        return datetime.strptime(cleaned, DATE_FORMAT).date().isoformat(), None
    except ValueError:
        return None, "MALFORMED_DATE"


def canonical_work_key(house: str, work_id: str | None) -> str | None:
    return f"{house}:{work_id}" if work_id else None


def classify_work_reference(value: Any) -> tuple[str | None, str]:
    label = clean_text(value)
    work_id = normalized_work_id(label)
    if work_id:
        return work_id, "RESOLVED"
    if label is None:
        return None, "BLANK_OR_UNRESOLVED_SOURCE_RECORD"
    if label.upper().startswith("NA-"):
        return None, "UNRESOLVED_SOURCE_WORK_REFERENCE"
    return None, "UNRESOLVED_SOURCE_WORK_REFERENCE"
