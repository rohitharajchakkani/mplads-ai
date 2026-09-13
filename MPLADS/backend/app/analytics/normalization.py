"""Authoritative text normalization used by public analytical filters."""
from __future__ import annotations

from sqlalchemy import String, func


def normalize_text(value: str | None) -> str | None:
    """Trim and collapse whitespace without changing source display values."""
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def normalize_house(value: str | None) -> str | None:
    normalized = normalize_text(value)
    if normalized is None:
        return None
    compact = normalized.replace("-", "_").replace(" ", "_").upper()
    aliases = {"LOKSABHA": "LOK_SABHA", "RAJYASABHA": "RAJYA_SABHA"}
    return aliases.get(compact.replace("_", ""), compact)


def normalized_column(column):
    """Comparable SQL expression for case/whitespace-insensitive selection.

    SQLite has no portable regular-expression replace. Repeating ``replace`` handles
    ordinary repeated source whitespace while retaining a cross-database expression.
    """
    value = func.trim(func.coalesce(column, ""))
    for _ in range(4):
        value = func.replace(value, "  ", " ")
    return func.lower(value.cast(String))


def normalized_equals(column, value: str):
    return normalized_column(column) == normalize_text(value).lower()


def normalized_contains(column, value: str):
    normalized = normalize_text(value)
    if normalized is None:
        return None
    return normalized_column(column).like(f"%{normalized.lower()}%")
