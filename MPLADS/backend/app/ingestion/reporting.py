"""Produce database-derived Phase 5 validation evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import func, select

from app.db.session import create_session_factory
from app.models import DatasetVersion, IngestionBatch, ValidationFinding


def render_validation_report(database_url: str) -> str:
    factory = create_session_factory(database_url)
    with factory() as session:
        batch = session.scalars(
            select(IngestionBatch).where(IngestionBatch.status == "VALIDATED").order_by(IngestionBatch.finished_at.desc())
        ).first()
        if batch is None:
            raise RuntimeError("No validated ingestion batch is available.")
        versions = session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == batch.id).order_by(DatasetVersion.house, DatasetVersion.dataset_type)).all()
        severities = dict(session.execute(select(ValidationFinding.severity, func.count()).where(ValidationFinding.batch_id == batch.id).group_by(ValidationFinding.severity)).all())
        codes = session.execute(select(ValidationFinding.code, func.count()).where(ValidationFinding.batch_id == batch.id).group_by(ValidationFinding.code).order_by(ValidationFinding.code)).all()
        summary = batch.summary or {}
    lines = [
        "# Validation report", "", f"Validated batch: `{batch.id}`.", "",
        f"Ingestion version: `{batch.ingestion_version}`. Application version: `{batch.application_version}`. Database status: `{batch.status}`.",
        "", "## Row outcomes", "", "| Dataset | House | Source | Staged | Valid | Warning | Rejected |", "|---|---|---:|---:|---:|---:|---:|",
    ]
    for version in versions:
        lines.append(f"| {version.dataset_type} | {version.house} | {version.source_row_count:,} | {version.staged_row_count:,} | {version.valid_row_count:,} | {version.warning_row_count:,} | {version.rejected_row_count:,} |")
    lines.extend(["", "## Findings", "", f"- Errors: {severities.get('ERROR', 0):,}", f"- Warnings: {severities.get('WARNING', 0):,}", "", "| Code | Count | Interpretation |", "|---|---:|---|"])
    meaning = {
        "BLANK_SOURCE_WORK_REFERENCE": "Retained source row has no usable Work ID/label.",
        "UNRESOLVED_SOURCE_WORK_REFERENCE": "Retained source work label cannot safely link to a canonical work.",
        "MALFORMED_DATE": "Preserved source text cannot be parsed as the observed date format.",
        "MISSING_DATE": "Date source value is blank.",
        "MISSING_MONEY": "Monetary source value is blank; it is not converted to zero.",
        "MISSING_CRITICAL_FIELD": "Required source field is blank; the staging record is retained and rejected from canonical promotion.",
    }
    lines.extend(f"| {code} | {count:,} | {meaning.get(code, 'See source-row finding.')} |" for code, count in codes)
    lines.extend([
        "",
        "Most `MALFORMED_DATE` findings are the source value `NA` in recommended-work `Sanction Date`; it indicates no parseable sanction date and remains raw source text. Two other values in that field are non-date numeric strings. The validation layer does not repair either condition.",
        "",
        "## Canonical output",
        "",
    ])
    lines.extend(f"- `{name}`: {count:,}" for name, count in summary.get("canonical", {}).items())
    lines.extend(["", "No source files were changed. House assignment is intake-derived because the workbooks do not have a House field. Rejected records remain traceable in staging and validation findings; unresolved records are retained without speculative linkage.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_validation_report(args.database_url), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
